# PowerShell version of the curl examples.
# Run each block in PowerShell.  Replace YOUR_KEY_HERE with the
# subscription key from https://comtradedeveloper.un.org/profile
# (or omit `-Headers @{...}` for the public preview).

$base = "https://comtradeapi.un.org"
$key  = "YOUR_KEY_HERE"  # leave as-is for public preview

# --------------------------------------------------------------------
# 1) Reference data — public, no key
# --------------------------------------------------------------------

# List of all reference tables
Invoke-RestMethod "$base/files/v1/app/reference/ListofReferences.json" | ConvertTo-Json -Depth 5

# Reporter countries
Invoke-RestMethod "$base/files/v1/app/reference/Reporters.json" | ConvertTo-Json -Depth 5

# HS 2022 (6-digit)
Invoke-RestMethod "$base/files/v1/app/reference/H6.json" | ConvertTo-Json -Depth 5


# --------------------------------------------------------------------
# 2) Trade data — public preview, no key, <=500 records
# --------------------------------------------------------------------

# India 2022 annual exports — all products, all partners
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&maxRecords=10"
(Invoke-RestMethod $url).data | Format-List

# India 2022 annual imports — all products, all partners
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=M&cmdCode=TOTAL&maxRecords=10"
(Invoke-RestMethod $url).data | Format-List

# India 2022 monthly exports — HS 7113 (jewellery)
$months = (1..12 | ForEach-Object { "2022{0:D2}" -f $_ }) -join ","
$url = "$base/public/v1/preview/C/M/HS?reportercode=699&period=$months&flowCode=X&cmdCode=7113&maxRecords=10"
(Invoke-RestMethod $url).data | Format-List

# India 2022 annual exports — HS chapter 30 (pharma)
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=30&maxRecords=10"
(Invoke-RestMethod $url).data | Format-List

# India 2022 annual exports to WORLD (partnerCode=0)
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=0&maxRecords=5"
(Invoke-RestMethod $url).data | Format-List

# India 2022 annual exports to USA (partnerCode=842)
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&partnerCode=842&maxRecords=5"
(Invoke-RestMethod $url).data | Format-List

# Count of records without downloading them
$url = "$base/public/v1/preview/C/A/HS?reportercode=699&period=2022&flowCode=X&cmdCode=TOTAL&countOnly=true"
Invoke-RestMethod $url


# --------------------------------------------------------------------
# 3) Trade data — authenticated, up to 250K records
# --------------------------------------------------------------------

$headers = @{ "Ocp-Apim-Subscription-Key" = $key }

# Full annual exports 2022 — up to 250K records
$url = "$base/data/v1/get/C/A/HS?reporterCode=699&period=2022&flowCode=X&cmdCode=TOTAL&maxRecords=250000"
(Invoke-RestMethod -Uri $url -Headers $headers).data | Format-List

# Trade balance — exports and imports side by side
$url = "$base/tools/v1/getTradeBalance/C/A/HS?reporterCode=699&period=2022&cmdCode=TOTAL&partnerCode=0"
(Invoke-RestMethod -Uri $url -Headers $headers).data | Format-List
