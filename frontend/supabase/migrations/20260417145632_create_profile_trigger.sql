/*
  # Auto-create profile on Supabase signup

  Creates a database function and trigger that automatically inserts
  a row into the `profiles` table whenever a new user is created
  in auth.users. Role and company info are read from app_metadata.
*/

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO profiles (id, name, role, company_id, is_admin)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'name', NEW.raw_user_meta_data->>'full_name', NEW.email, ''),
    COALESCE(NEW.raw_app_meta_data->>'role', NEW.raw_user_meta_data->>'role', 'client'),
    NULLIF((NEW.raw_app_meta_data->>'company_id')::bigint, 0),
    COALESCE((NEW.raw_app_meta_data->>'is_admin')::boolean, false)
  )
  ON CONFLICT (id) DO UPDATE SET
    name       = EXCLUDED.name,
    role       = EXCLUDED.role,
    company_id = EXCLUDED.company_id,
    is_admin   = EXCLUDED.is_admin;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();
