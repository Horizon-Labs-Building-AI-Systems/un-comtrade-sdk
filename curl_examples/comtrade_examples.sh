# ====================================================================
# UN Comtrade API — curl examples
# ====================================================================
# Replace YOUR_KEY_HERE with the subscription key from
# https://comtradedeveloper.un.org/profile — or omit it for the
# public preview endpoints (≤500 records per call).
#
# NOTE: the preview endpoint is case-sensitive on the
# `reportercode` parameter (all lowercase). The data endpoint
# accepts `reporterCode` (camelCase) — see note below each example.
# ====================================================================

# --------------------------------------------------------------------
# 1) Reference data — public, no key
# --------------------------------------------------------------------

# List every available reference table
curl -s "https://comtradeapi.un.org/files/v1/app/reference/ListofReferences.json" | jq .

# Get the full list of reporter countries
curl -s "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json" | jq '.results | length'

# Get the full HS (combined) classification
curl -s "https://comtradeapi.un.org/files/v1/app/reference/HS.json" -o hs.json

# Get the HS 2022 (6-digit) classification
curl -s "https://comtradeapi.un.org/files/v1/app/reference/H6.json" -o hs_2022.json

# Get the list of partner countries/areas
curl -s "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json" -o partners.json


# --------------------------------------------------------------------
# 2) Trade data — public preview, no key, ≤500 records
# --------------------------------------------------------------------

# India 2022 annual exports — all products, all partners
# reportercode is lowercase here (preview endpoint quirk)
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&maxRecords=10" | jq .

# India 2022 annual imports — all products, all partners
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=M&cmdCode=TOTAL&maxRecords=10" | jq .

# India 2022 monthly exports — HS 7113 (jewellery)
curl -s "https://comtradeapi.un.org/public/v1/preview/C/M/HS?reportercode=699&period=202201,202202,202203,202204,202205,202206,202207,202208,202209,202210,202211,202212&flowCode=X&cmdCode=7113&maxRecords=10" | jq .

# India 2022 annual exports — HS chapter 30 (pharma)
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=30&maxRecords=10" | jq .

# India 2022 annual exports to WORLD (partnerCode=0)
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=0&maxRecords=5" | jq .

# India 2022 annual exports to USA (partnerCode=842)
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=842&maxRecords=5" | jq .

# India 2022 annual trade with China (partnerCode=156), imports only
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=M&cmdCode=TOTAL&partnerCode=156&maxRecords=5" | jq .

# Multiple periods in one call
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2020,2021,2022&flowCode=X&cmdCode=TOTAL&maxRecords=10" | jq .

# All partner totals for India in 2022 — single record, world total
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=0&maxRecords=1" | jq .

# Count of records without downloading them all
curl -s "https://comtradeapi.un.org/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&countOnly=true" | jq .


# --------------------------------------------------------------------
# 3) Trade data — authenticated, up to 250K records
# --------------------------------------------------------------------
# Set the subscription key in the URL OR as the Ocp-Apim-Subscription-Key
# header (Azure API Management style — the documentation accepts both).

# Full annual exports 2022 — up to 250K records
curl -s "https://comtradeapi.un.org/data/v1/get/C/A/HS?reporterCode=699&period=2022&flowCode=X&cmdCode=TOTAL&maxRecords=250000&subscription-key=YOUR_KEY_HERE" | jq .

# Annual exports for the last 5 years (one call, all records)
curl -s "https://comtradeapi.un.org/data/v1/get/C/A/HS?reporterCode=699&period=2018,2019,2020,2021,2022&flowCode=X&cmdCode=TOTAL&maxRecords=250000&subscription-key=YOUR_KEY_HERE" | jq .

# Trade balance — exports and imports side by side
curl -s "https://comtradeapi.un.org/tools/v1/getTradeBalance/C/A/HS?reporterCode=699&period=2022&cmdCode=TOTAL&partnerCode=0&subscription-key=YOUR_KEY_HERE" | jq .

# Tariffline data — line-level records (more detail)
curl -s "https://comtradeapi.un.org/data/v1/getTariffline/C/A/HS?reporterCode=699&period=2022&flowCode=X&cmdCode=7113&subscription-key=YOUR_KEY_HERE" | jq .

# Trade matrix — official trade complemented by estimates (e.g. world export)
curl -s "https://comtradeapi.un.org/data/v1/getTradeMatrix/C/A/TM?reporterCode=0&period=2022&flowCode=X&cmdCode=ag1&subscription-key=YOUR_KEY_HERE" | jq .
