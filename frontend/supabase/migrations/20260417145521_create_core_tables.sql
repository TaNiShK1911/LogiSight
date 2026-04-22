/*
  # LogiSight Core Tables (Part 1 of 2)

  Creates all tables first, then RLS policies are added in part 2
  since some policies cross-reference other tables.

  Tables: companies, profiles, countries, currencies, airports,
          charges, charge_aliases, quotes, quote_charges,
          invoices, invoice_charges, anomalies, tracking_events
*/

-- ─── COMPANIES ───
CREATE TABLE IF NOT EXISTS companies (
  id          bigserial PRIMARY KEY,
  name        text        NOT NULL,
  short_name  text        NOT NULL,
  type        text        NOT NULL CHECK (type IN ('client', 'forwarder')),
  address     text,
  city        text,
  country     text,
  is_active   boolean     NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ─── PROFILES (extends auth.users) ───
CREATE TABLE IF NOT EXISTS profiles (
  id           uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  company_id   bigint REFERENCES companies(id),
  name         text        NOT NULL DEFAULT '',
  role         text        NOT NULL DEFAULT 'client' CHECK (role IN ('super_admin', 'client', 'forwarder')),
  is_admin     boolean     NOT NULL DEFAULT false,
  is_active    boolean     NOT NULL DEFAULT true,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- ─── COUNTRIES ───
CREATE TABLE IF NOT EXISTS countries (
  id         bigserial PRIMARY KEY,
  name       text    NOT NULL UNIQUE,
  short_name text    NOT NULL UNIQUE,
  is_active  boolean NOT NULL DEFAULT true
);

-- ─── CURRENCIES ───
CREATE TABLE IF NOT EXISTS currencies (
  id         bigserial PRIMARY KEY,
  name       text    NOT NULL UNIQUE,
  short_name text    NOT NULL UNIQUE,
  is_active  boolean NOT NULL DEFAULT true
);

-- ─── AIRPORTS ───
CREATE TABLE IF NOT EXISTS airports (
  id         bigserial PRIMARY KEY,
  name       text    NOT NULL,
  iata_code  text    NOT NULL UNIQUE,
  country_id bigint  REFERENCES countries(id),
  is_active  boolean NOT NULL DEFAULT true
);

-- ─── CHARGES (Charge Master) ───
CREATE TABLE IF NOT EXISTS charges (
  id          bigserial PRIMARY KEY,
  company_id  bigint      NOT NULL REFERENCES companies(id),
  name        text        NOT NULL,
  short_name  text        NOT NULL,
  is_active   boolean     NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (company_id, name),
  UNIQUE (company_id, short_name)
);

-- ─── CHARGE ALIASES ───
CREATE TABLE IF NOT EXISTS charge_aliases (
  id        bigserial PRIMARY KEY,
  charge_id bigint NOT NULL REFERENCES charges(id) ON DELETE CASCADE,
  alias     text   NOT NULL,
  UNIQUE (charge_id, alias)
);

-- ─── QUOTES ───
CREATE TABLE IF NOT EXISTS quotes (
  id                       bigserial PRIMARY KEY,
  forwarder_id             bigint      NOT NULL REFERENCES companies(id),
  buyer_id                 bigint      NOT NULL REFERENCES companies(id),
  quote_ref                text        NOT NULL UNIQUE,
  origin_airport_id        bigint      REFERENCES airports(id),
  destination_airport_id   bigint      REFERENCES airports(id),
  tracking_number          text        NOT NULL,
  gross_weight             numeric     NOT NULL DEFAULT 0,
  volumetric_weight        numeric     NOT NULL DEFAULT 0,
  chargeable_weight        numeric     NOT NULL DEFAULT 0,
  currency_id              bigint      REFERENCES currencies(id),
  status                   text        NOT NULL DEFAULT 'SUBMITTED' CHECK (status IN ('SUBMITTED','ACCEPTED','REJECTED')),
  rejection_note           text,
  created_at               timestamptz NOT NULL DEFAULT now()
);

-- ─── QUOTE CHARGES ───
CREATE TABLE IF NOT EXISTS quote_charges (
  id                  bigserial PRIMARY KEY,
  quote_id            bigint      NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  raw_charge_name     text        NOT NULL,
  mapped_charge_id    bigint      REFERENCES charges(id),
  mapped_charge_name  text,
  similarity_score    numeric,
  mapping_tier        text        NOT NULL DEFAULT 'UNMAPPED' CHECK (mapping_tier IN ('DICTIONARY','VECTOR','LLM','HUMAN','UNMAPPED')),
  low_confidence      boolean     NOT NULL DEFAULT false,
  rate                numeric     NOT NULL DEFAULT 0,
  basis               text        NOT NULL DEFAULT 'Per Shipment' CHECK (basis IN ('Per KG','Per Shipment','Per CBM')),
  qty                 numeric     NOT NULL DEFAULT 1,
  amount              numeric     NOT NULL DEFAULT 0
);

-- ─── INVOICES ───
CREATE TABLE IF NOT EXISTS invoices (
  id              bigserial PRIMARY KEY,
  quote_id        bigint      NOT NULL REFERENCES quotes(id),
  invoice_number  text        NOT NULL,
  invoice_date    date        NOT NULL,
  file_path       text        NOT NULL DEFAULT '',
  uploaded_at     timestamptz NOT NULL DEFAULT now()
);

-- ─── INVOICE CHARGES ───
CREATE TABLE IF NOT EXISTS invoice_charges (
  id                  bigserial PRIMARY KEY,
  invoice_id          bigint      NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  raw_charge_name     text        NOT NULL,
  mapped_charge_id    bigint      REFERENCES charges(id),
  mapped_charge_name  text,
  similarity_score    numeric,
  mapping_tier        text        NOT NULL DEFAULT 'UNMAPPED' CHECK (mapping_tier IN ('DICTIONARY','VECTOR','LLM','HUMAN','UNMAPPED')),
  low_confidence      boolean     NOT NULL DEFAULT false,
  rate                numeric     NOT NULL DEFAULT 0,
  basis               text        NOT NULL DEFAULT 'Per Shipment' CHECK (basis IN ('Per KG','Per Shipment','Per CBM')),
  qty                 numeric     NOT NULL DEFAULT 1,
  amount              numeric     NOT NULL DEFAULT 0
);

-- ─── ANOMALIES ───
CREATE TABLE IF NOT EXISTS anomalies (
  id                  bigserial PRIMARY KEY,
  invoice_id          bigint      NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  invoice_charge_id   bigint      REFERENCES invoice_charges(id),
  flag_type           text        NOT NULL CHECK (flag_type IN ('AMOUNT_MISMATCH','RATE_MISMATCH','BASIS_MISMATCH','UNEXPECTED_CHARGE','MISSING_CHARGE','DUPLICATE_INVOICE')),
  description         text        NOT NULL DEFAULT '',
  variance            numeric
);

-- ─── TRACKING EVENTS ───
CREATE TABLE IF NOT EXISTS tracking_events (
  id          bigserial PRIMARY KEY,
  quote_id    bigint      NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  event_time  timestamptz NOT NULL DEFAULT now(),
  location    text        NOT NULL DEFAULT '',
  status      text        NOT NULL DEFAULT '',
  description text        NOT NULL DEFAULT ''
);

-- ─── INDEXES ───
CREATE INDEX IF NOT EXISTS idx_profiles_company_id       ON profiles(company_id);
CREATE INDEX IF NOT EXISTS idx_charges_company_id        ON charges(company_id);
CREATE INDEX IF NOT EXISTS idx_charge_aliases_charge_id  ON charge_aliases(charge_id);
CREATE INDEX IF NOT EXISTS idx_quotes_forwarder_id       ON quotes(forwarder_id);
CREATE INDEX IF NOT EXISTS idx_quotes_buyer_id           ON quotes(buyer_id);
CREATE INDEX IF NOT EXISTS idx_quote_charges_quote_id    ON quote_charges(quote_id);
CREATE INDEX IF NOT EXISTS idx_invoices_quote_id         ON invoices(quote_id);
CREATE INDEX IF NOT EXISTS idx_invoice_charges_id        ON invoice_charges(invoice_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_invoice_id      ON anomalies(invoice_id);
CREATE INDEX IF NOT EXISTS idx_tracking_events_quote_id  ON tracking_events(quote_id);
