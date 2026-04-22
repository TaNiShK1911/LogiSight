/*
  # Seed Master Data

  Inserts:
  - Common currencies used in freight (USD, EUR, SGD, GBP, AED, CNY, JPY, AUD)
  - Major freight/logistics countries
  - Top international cargo airports (IATA codes)
*/

-- ─── CURRENCIES ───
INSERT INTO currencies (name, short_name) VALUES
  ('US Dollar',            'USD'),
  ('Euro',                 'EUR'),
  ('Singapore Dollar',     'SGD'),
  ('British Pound',        'GBP'),
  ('UAE Dirham',           'AED'),
  ('Chinese Yuan',         'CNY'),
  ('Japanese Yen',         'JPY'),
  ('Australian Dollar',    'AUD'),
  ('Hong Kong Dollar',     'HKD'),
  ('Swiss Franc',          'CHF')
ON CONFLICT (short_name) DO NOTHING;

-- ─── COUNTRIES ───
INSERT INTO countries (name, short_name) VALUES
  ('United States',        'US'),
  ('United Kingdom',       'GB'),
  ('Germany',              'DE'),
  ('Singapore',            'SG'),
  ('China',                'CN'),
  ('Japan',                'JP'),
  ('United Arab Emirates', 'AE'),
  ('Australia',            'AU'),
  ('Hong Kong',            'HK'),
  ('Netherlands',          'NL'),
  ('South Korea',          'KR'),
  ('India',                'IN'),
  ('France',               'FR'),
  ('Canada',               'CA'),
  ('Switzerland',          'CH')
ON CONFLICT (short_name) DO NOTHING;

-- ─── AIRPORTS ───
INSERT INTO airports (name, iata_code, country_id) VALUES
  ('John F. Kennedy International Airport',     'JFK', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Los Angeles International Airport',          'LAX', (SELECT id FROM countries WHERE short_name = 'US')),
  ('O''Hare International Airport',              'ORD', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Hartsfield-Jackson Atlanta',                 'ATL', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Miami International Airport',               'MIA', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Heathrow Airport',                          'LHR', (SELECT id FROM countries WHERE short_name = 'GB')),
  ('Frankfurt Airport',                         'FRA', (SELECT id FROM countries WHERE short_name = 'DE')),
  ('Singapore Changi Airport',                  'SIN', (SELECT id FROM countries WHERE short_name = 'SG')),
  ('Beijing Capital International Airport',     'PEK', (SELECT id FROM countries WHERE short_name = 'CN')),
  ('Shanghai Pudong International Airport',     'PVG', (SELECT id FROM countries WHERE short_name = 'CN')),
  ('Guangzhou Baiyun International Airport',    'CAN', (SELECT id FROM countries WHERE short_name = 'CN')),
  ('Narita International Airport',              'NRT', (SELECT id FROM countries WHERE short_name = 'JP')),
  ('Dubai International Airport',              'DXB', (SELECT id FROM countries WHERE short_name = 'AE')),
  ('Sydney Kingsford Smith Airport',            'SYD', (SELECT id FROM countries WHERE short_name = 'AU')),
  ('Hong Kong International Airport',           'HKG', (SELECT id FROM countries WHERE short_name = 'HK')),
  ('Amsterdam Airport Schiphol',                'AMS', (SELECT id FROM countries WHERE short_name = 'NL')),
  ('Incheon International Airport',             'ICN', (SELECT id FROM countries WHERE short_name = 'KR')),
  ('Indira Gandhi International Airport',       'DEL', (SELECT id FROM countries WHERE short_name = 'IN')),
  ('Chhatrapati Shivaji International Airport', 'BOM', (SELECT id FROM countries WHERE short_name = 'IN')),
  ('Charles de Gaulle Airport',                 'CDG', (SELECT id FROM countries WHERE short_name = 'FR')),
  ('Toronto Pearson International Airport',     'YYZ', (SELECT id FROM countries WHERE short_name = 'CA')),
  ('Zurich Airport',                            'ZRH', (SELECT id FROM countries WHERE short_name = 'CH')),
  ('Memphis International Airport',             'MEM', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Louisville Muhammad Ali International',     'SDF', (SELECT id FROM countries WHERE short_name = 'US')),
  ('Anchorage Ted Stevens International',       'ANC', (SELECT id FROM countries WHERE short_name = 'US'))
ON CONFLICT (iata_code) DO NOTHING;
