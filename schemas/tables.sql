-- Represents a House Financial Disclosure report
create table if not exists reports (
    -- The report's filing ID, which uniquely identifies it
    report_id integer primary key on conflict ignore,
    -- The full name of the House Representative to whom this report belongs
    representative_name text,
    -- The date on which this report was certified and signed by the representative
    signed_date text,
    -- The date and time at which this record was created
    created_at text
);

-- Represents a transaction within a House Financial Disclosure report
create table if not exists transactions (
    -- An MD5 hash of the report ID, asset ID, and the transaction date
    transaction_id integer primary key on conflict ignore,
    -- The ID of the report (record) this transaction belongs to
    report_id integer references report (report_id),
    asset_name text,
    asset_type text,
    asset_ticker text,
    -- TODO: Only "New" seems to be present, additional values would provide more context as to what this attribute means
    filing_status text,
    subholding_of text,
    description text,
    comment text,
    -- The type of transaction (eg. purchase - "P", sale - "S")
    type text,
    -- The date on which this transaction was made
    transaction_date text,
    -- The date on which this transaction was notified to the public ?
    notification_date text,
    -- The minimum amount of the range processed in total on this transaction
    amount_min integer,
    -- The maximum amount of the range processed in total on this transaction
    amount_max integer,
    -- The cleansed text extracted from the report PDF from which this transaction was created
    match_text text,
    -- The date and time at which this record was created
    created_at text
);

-- NOTE: The report parser isn't good enough to cleanly extract asset name on
-- occasion, so I'm just going to denormalise the transaction table and include
-- asset attributes in it to avoid messy joins. The ticker is likely the most
-- reliable way to query transactions by asset, since stocks are likely the 
-- most meaningful assets in this context
-- create table if not exists assets (
--     -- An MD5 hash of the asset name and type
--     asset_id primary key on conflict ignore,
--     -- The name of the asset
--     name text,
--     -- The type of asset it is (eg. stock - "ST")
--     type text,
--     -- The ticker symbol for the asset if it is a stock, null otherwise
--     ticker text,
--     -- The date and time at which this record was created
--     created_at text
-- );
