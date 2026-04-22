/*
  # LogiSight RLS Policies (Part 2 of 2)

  Enables Row Level Security and adds access policies for all tables.
  All data is strictly scoped by company_id extracted from the user's profile.

  Security model:
  - super_admin: full read/write on companies and profiles
  - client: access to their own company's charges, buyer-side quotes/invoices/anomalies
  - forwarder: access to their submitted quotes and uploaded invoices (raw names only — masking enforced at app layer)
  - Public master data (airports, currencies, countries): read-only for all authenticated users
*/

-- ─── COMPANIES ───
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members view own company"
  ON companies FOR SELECT TO authenticated
  USING (
    id IN (SELECT company_id FROM profiles WHERE id = auth.uid())
    OR EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin')
  );

CREATE POLICY "Super admin inserts companies"
  ON companies FOR INSERT TO authenticated
  WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin'));

CREATE POLICY "Super admin updates companies"
  ON companies FOR UPDATE TO authenticated
  USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin'))
  WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin'));

-- ─── PROFILES ───
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own profile"
  ON profiles FOR SELECT TO authenticated
  USING (id = auth.uid());

CREATE POLICY "Same company members view profiles"
  ON profiles FOR SELECT TO authenticated
  USING (
    company_id IS NOT NULL
    AND company_id IN (SELECT company_id FROM profiles WHERE id = auth.uid())
  );

CREATE POLICY "Users update own profile"
  ON profiles FOR UPDATE TO authenticated
  USING (id = auth.uid())
  WITH CHECK (id = auth.uid());

CREATE POLICY "Super admin inserts profiles"
  ON profiles FOR INSERT TO authenticated
  WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'super_admin'));

CREATE POLICY "Self insert profile on signup"
  ON profiles FOR INSERT TO authenticated
  WITH CHECK (id = auth.uid());

-- ─── COUNTRIES ───
ALTER TABLE countries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read countries"
  ON countries FOR SELECT TO authenticated USING (true);

-- ─── CURRENCIES ───
ALTER TABLE currencies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read currencies"
  ON currencies FOR SELECT TO authenticated USING (true);

-- ─── AIRPORTS ───
ALTER TABLE airports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated read airports"
  ON airports FOR SELECT TO authenticated USING (true);

-- ─── CHARGES ───
ALTER TABLE charges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Client members view own charges"
  ON charges FOR SELECT TO authenticated
  USING (
    company_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
  );

CREATE POLICY "Client members insert charges"
  ON charges FOR INSERT TO authenticated
  WITH CHECK (
    company_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
  );

CREATE POLICY "Client members update charges"
  ON charges FOR UPDATE TO authenticated
  USING (company_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'))
  WITH CHECK (company_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'));

-- ─── CHARGE ALIASES ───
ALTER TABLE charge_aliases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Client members view own aliases"
  ON charge_aliases FOR SELECT TO authenticated
  USING (
    charge_id IN (
      SELECT c.id FROM charges c
      JOIN profiles p ON p.company_id = c.company_id
      WHERE p.id = auth.uid() AND p.role = 'client'
    )
  );

CREATE POLICY "Client members insert aliases"
  ON charge_aliases FOR INSERT TO authenticated
  WITH CHECK (
    charge_id IN (
      SELECT c.id FROM charges c
      JOIN profiles p ON p.company_id = c.company_id
      WHERE p.id = auth.uid() AND p.role = 'client'
    )
  );

CREATE POLICY "Client members delete aliases"
  ON charge_aliases FOR DELETE TO authenticated
  USING (
    charge_id IN (
      SELECT c.id FROM charges c
      JOIN profiles p ON p.company_id = c.company_id
      WHERE p.id = auth.uid() AND p.role = 'client'
    )
  );

-- ─── QUOTES ───
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Forwarder views own quotes"
  ON quotes FOR SELECT TO authenticated
  USING (forwarder_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'));

CREATE POLICY "Buyer views quotes addressed to them"
  ON quotes FOR SELECT TO authenticated
  USING (buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'));

CREATE POLICY "Forwarder inserts quotes"
  ON quotes FOR INSERT TO authenticated
  WITH CHECK (forwarder_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'));

CREATE POLICY "Buyer updates quote status"
  ON quotes FOR UPDATE TO authenticated
  USING (buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'))
  WITH CHECK (buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'));

-- ─── QUOTE CHARGES ───
ALTER TABLE quote_charges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Forwarder views own quote charges"
  ON quote_charges FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );

CREATE POLICY "Buyer views quote charges"
  ON quote_charges FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE buyer_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'
      )
    )
  );

CREATE POLICY "Forwarder inserts quote charges"
  ON quote_charges FOR INSERT TO authenticated
  WITH CHECK (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );

CREATE POLICY "Buyer updates quote charge mapping"
  ON quote_charges FOR UPDATE TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE buyer_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'
      )
    )
  )
  WITH CHECK (
    quote_id IN (
      SELECT id FROM quotes WHERE buyer_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'
      )
    )
  );

-- ─── INVOICES ───
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Forwarder views own invoices"
  ON invoices FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );

CREATE POLICY "Buyer views invoices for their quotes"
  ON invoices FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE buyer_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'
      )
    )
  );

CREATE POLICY "Forwarder inserts invoices"
  ON invoices FOR INSERT TO authenticated
  WITH CHECK (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );

-- ─── INVOICE CHARGES ───
ALTER TABLE invoice_charges ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Buyer views invoice charges"
  ON invoice_charges FOR SELECT TO authenticated
  USING (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
    )
  );

CREATE POLICY "Forwarder views own invoice charges"
  ON invoice_charges FOR SELECT TO authenticated
  USING (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.forwarder_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder')
    )
  );

CREATE POLICY "Forwarder inserts invoice charges"
  ON invoice_charges FOR INSERT TO authenticated
  WITH CHECK (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.forwarder_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder')
    )
  );

CREATE POLICY "Buyer updates invoice charge mapping"
  ON invoice_charges FOR UPDATE TO authenticated
  USING (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
    )
  )
  WITH CHECK (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
    )
  );

-- ─── ANOMALIES ───
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Buyer views anomalies"
  ON anomalies FOR SELECT TO authenticated
  USING (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
    )
  );

CREATE POLICY "Buyer inserts anomalies"
  ON anomalies FOR INSERT TO authenticated
  WITH CHECK (
    invoice_id IN (
      SELECT inv.id FROM invoices inv
      JOIN quotes q ON q.id = inv.quote_id
      WHERE q.buyer_id IN (SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client')
    )
  );

-- ─── TRACKING EVENTS ───
ALTER TABLE tracking_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Buyer views tracking for their quotes"
  ON tracking_events FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE buyer_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'client'
      )
    )
  );

CREATE POLICY "Forwarder views tracking for their quotes"
  ON tracking_events FOR SELECT TO authenticated
  USING (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );

CREATE POLICY "Forwarder inserts tracking events"
  ON tracking_events FOR INSERT TO authenticated
  WITH CHECK (
    quote_id IN (
      SELECT id FROM quotes WHERE forwarder_id IN (
        SELECT company_id FROM profiles WHERE id = auth.uid() AND role = 'forwarder'
      )
    )
  );
