/*
  # Seed Test Companies and User Accounts

  Creates test data for development and QA purposes.

  ## Companies
  - AcmeCo Logistics (client)
  - FastFreight Co (forwarder)

  ## Users  (password for all: TestPass123!)
  - super_admin@logisight.dev  — Super Admin
  - client.admin@acmeco.dev    — Client Admin   (AcmeCo Logistics)
  - client.user@acmeco.dev     — Client User    (AcmeCo Logistics)
  - fwd.admin@fastfreight.dev  — Forwarder Admin (FastFreight Co)
  - fwd.user@fastfreight.dev   — Forwarder User  (FastFreight Co)
*/

CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO companies (name, short_name, type, city, country, is_active)
VALUES
  ('AcmeCo Logistics', 'ACL', 'client',    'Singapore', 'Singapore', true),
  ('FastFreight Co',   'FFC', 'forwarder', 'Singapore', 'Singapore', true)
ON CONFLICT DO NOTHING;

DO $$
DECLARE
  v_pass       text   := crypt('TestPass123!', gen_salt('bf'));
  v_client_cid bigint;
  v_fwd_cid    bigint;
  v_uid        uuid;

  v_emails     text[]   := ARRAY['super_admin@logisight.dev','client.admin@acmeco.dev','client.user@acmeco.dev','fwd.admin@fastfreight.dev','fwd.user@fastfreight.dev'];
  v_names      text[]   := ARRAY['Super Admin','Client Admin','Client User','Forwarder Admin','Forwarder User'];
  v_roles      text[]   := ARRAY['super_admin','client','client','forwarder','forwarder'];
  v_is_admins  boolean[] := ARRAY[true, true, false, true, false];
  v_cids       bigint[];
  i            int;
BEGIN
  SELECT id INTO v_client_cid FROM companies WHERE short_name = 'ACL';
  SELECT id INTO v_fwd_cid    FROM companies WHERE short_name = 'FFC';

  v_cids := ARRAY[NULL::bigint, v_client_cid, v_client_cid, v_fwd_cid, v_fwd_cid];

  FOR i IN 1..5 LOOP
    SELECT id INTO v_uid FROM auth.users WHERE email = v_emails[i];
    IF v_uid IS NOT NULL THEN
      CONTINUE;
    END IF;

    v_uid := gen_random_uuid();

    INSERT INTO auth.users (
      instance_id, id, aud, role,
      email, encrypted_password,
      email_confirmed_at,
      raw_app_meta_data,
      raw_user_meta_data,
      created_at, updated_at,
      confirmation_token, recovery_token,
      is_sso_user
    ) VALUES (
      '00000000-0000-0000-0000-000000000000',
      v_uid, 'authenticated', 'authenticated',
      v_emails[i], v_pass,
      now(),
      jsonb_build_object(
        'provider', 'email',
        'providers', ARRAY['email'],
        'role', v_roles[i],
        'company_id', v_cids[i],
        'is_admin', v_is_admins[i]
      ),
      jsonb_build_object(
        'name', v_names[i],
        'role', v_roles[i],
        'company_id', v_cids[i],
        'is_admin', v_is_admins[i]
      ),
      now(), now(),
      '', '',
      false
    );

    INSERT INTO auth.identities (
      id, user_id, identity_data,
      provider, provider_id,
      last_sign_in_at, created_at, updated_at
    ) VALUES (
      gen_random_uuid(),
      v_uid,
      jsonb_build_object('sub', v_uid::text, 'email', v_emails[i]),
      'email',
      v_uid::text,
      now(), now(), now()
    );

    INSERT INTO profiles (id, company_id, name, role, is_admin, is_active)
    VALUES (v_uid, v_cids[i], v_names[i], v_roles[i], v_is_admins[i], true)
    ON CONFLICT (id) DO UPDATE
      SET company_id = EXCLUDED.company_id,
          name       = EXCLUDED.name,
          role       = EXCLUDED.role,
          is_admin   = EXCLUDED.is_admin;
  END LOOP;
END $$;
