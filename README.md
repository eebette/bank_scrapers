# Table of Contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->

- [Introduction](#introduction)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Usage](#usage)
- [Drivers](#drivers)
  - [BECU](#becu)
  - [Chase](#chase)
  - [Fidelity NetBenefits](#fidelity-netbenefits)
  - [RoundPoint](#roundpoint)
  - [SMBC Prestia](#smbc-prestia)
  - [UHFCU](#uhfcu)
  - [Vanguard](#vanguard)
  - [Zillow](#zillow)
- [API Wrappers](#api-wrappers)
  - [Kraken](#kraken)
- [Disclaimer](#disclaimer)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Quick Start 

```shell
pip install bank_scrapers
```

```shell
bank-scrape {subcommand} $LOGIN_USER $LOGIN_PASS
```

# Introduction

`bank_scrapers` is a library containing drivers for scraping account information from various financial websites. 

Since most traditional financial institutions don't provide an API for accessing one's account data, most of these
drivers utilize `Selenium` to impersonate the user using the provided credentials.

# Getting Started

## Installation

### `stable`
```shell
pip install bank_scrapers
```


### `experimental`
```shell
pip install git+https://github.com/eebette/bank_scrapers.git
```

## Usage

> 💡 Usage examples for each driver are listed in that driver's documentation

### CLI

#### For general info and complete usage documentation
```shell
bank-scrape -h
```

#### General usage pattern
```shell
bank-scrape {subcommand} $LOGIN_USER $LOGIN_PASS
```

### API

API results are returned as a Python list of pandas dataframes, containing relevant data scraped from the site. See each
 driver's section for info on what is in that driver's return tables. 

```python
from bank_scrapers.scrapers.becu.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```

#### Drivers that need a tmp directory

Some drivers download the accounts data and process the downloaded file. This requires the use of a temp directory to
 use as Chromium's downloads folder, and **the location of this folder must be specified in `get_accounts_info()`**.

> ❗️Selenium often has issues writing to `/tmp/` in Linux distributions, hence this requirement in the code.

> ❗️**NOTE** `tmp_dir` MUST be empty for this function to work

```python
from bank_scrapers.scrapers.fidelity_netbenefits.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}", tmp_dir="~/tmp")
for t in tables:
  print(t.to_string())
```

    
# Drivers

These are all written in Python using the Selenium driver and, for the most part, try to simulate the real user
experience/workflow as seen in the eyes of the website provider. 

## BECU

[Boeing Enterprises Credit Union](https://www.becu.org/)

### About

This is a Selenium driver that logs in using provided credentials and reads account info from the landing page.

> ❗️Driver does NOT currently support MFA
> 
### Example Usage

#### CLI
```shell
bank-scrape becu $LOGIN_USER $LOGIN_PASS
```
#### API
```python
from bank_scrapers.scrapers.becu.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```
#### Example Result
```
   Account  YTD Interest  Current Balance  Available Balance
##########          #.##          ####.##            ####.##
##########         ##.##         #####.##           #####.##
##########        ###.##         #####.##           #####.##
 Account  Current Balance  Available Credit
    ####           ###.##           #####.#
```

### Return Schema

#### For non-loan Account
| Column Name       |
|-------------------|
| Account           |
| YTD Interest      |
| Current Balance   |
| Available Balance |

#### For Credit Account
| Column Name      |
|------------------|
| Account          |
| Current Balance  |
| Available Credit |

## Chase

[Chase Banking](https://www.chase.com/)

### About

This is a Selenium driver that logs in using provided credentials, navigates 2FA, navigates to the detail account info 
from the landing page, and reads the account info from the page.

> ✔️ Driver supports handling of 2FA

> ❗️This driver is designed to crawl and pull data for Chase credit card services **only**. Chase shared bank accounts
> are currently not in the scope of this project

### Example Usage

#### CLI
```shell
bank-scrape chase $LOGIN_USER $LOGIN_PASS
```
#### API
```python
from bank_scrapers.scrapers.chase.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```
#### Example 2FA Workflow
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
0: TEXT ME
1: xxx-xxx-####
2: xxx-xxx-####
3: CALL ME
4: xxx-xxx-####
5: xxx-xxx-####
6: Call us - 1-877-242-7372
Please select one: {user_choose_2fa_option}
Enter 2FA Code: {user_enters_2fa_code}
```
#### Example Result
```
Current balance Pending charges Available credit Total credit limit Next closing date Balance on last statement Remaining statement balance Payments are due on the
        ####.##          ###.##         #####.##           #####.##             ####              ####.#######                     ####.##                      #.
Last payment Minimum payment Automatic Payments
####.#######      ##.#######                   
Points available
          ######
Cash advance balance Available for cash advance Cash advance limit
                #.##                    ####.##            ####.##
Purchase APR Cash advance APR
       ##.##            ##.##
Program details
           
```

### Return Schema

Provides int-ified values for each of the columns. 

> ❗️Dates will be converted to their spreadsheet friendly int-representation

> ❗️Any text values are dropped. Most notably this affects `Automatic Payments` and `Program details` columns, which are
> currently out of the scope of this project

#### Balance Info
| Column Name                 |
|-----------------------------|
| Current balance             |
| Pending charges             |
| Available credit            |
| Total credit limit          |
| Next closing date           |
| Balance on last statement   |
| Remaining statement balance |
| Payments are due on the     |

#### Payment Info
| Column Name        |
|--------------------|
| Last payment       |
| Minimum payment    |
| Automatic Payments |

#### Points Info
| Column Name      |
|------------------|
| Points available |

#### APR Info
| Column Name       |
|-------------------|
| Purchase APR      |
| Cash advance APR  |

#### Program Details
| Column Name      |
|------------------|
| Program details  |

## Fidelity NetBenefits

[Fidelity NetBenefits](https://nb.fidelity.com/)

> ❗️This driver is designed to work on the webpage for Fidelity NetBenefits, which is Fidelity's net interface for
> 401(k) holders and stock plan participants for various companies. It is not designed to work for general brokerage 
> account holders, though I suspect it would work with minimal effort

> ️✔️ This driver will pull holdings info for all Fidelity accounts for the account holder, including general brokerage
> accounts

### About

This is a Selenium driver that logs in using provided credentials, navigates 2FA, navigates to the detail account info
from the landing page for Fidelity NetBenefits. 

Instead of scraping the user's account info from the page, this driver will navigate to the user's positions summary and
 download the accounts info provided by Fidelity using a folder of the user's choice

> ✔️ Driver supports handling of 2FA

### Example Usage

#### CLI
```shell
bank-scrape fidelity-nb $LOGIN_USER $LOGIN_PASS
```

> 💡 The CLI backend handles the creation of a tmp directory in the user's home directory by default. The API doesn't
> have this functionality

#### API
```python
from bank_scrapers.scrapers.fidelity_netbenefits.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}", tmp_dir="~/tmp")
for t in tables:
  print(t.to_string())
```

> ❗️**NOTE** `tmp_dir` MUST be empty for this function to work

#### Example 2FA Workflow
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
0: Use *...*@*****.***
1: Use *...*@**.**
2: Use *...*@******.***
Please select one: {user_choose_2fa_option}
Enter 2FA Code: {user_enters_2fa_code}
```

#### Example Result
```
Account Number        Account Name     Symbol           Description  Quantity Last Price Last Price Change Current Value Today's Gain/Loss Dollar Today's Gain/Loss Percent Total Gain/Loss Dollar Total Gain/Loss Percent Percent Of Account Cost Basis Total Average Cost Basis  Type
     *########    ********** - ***    *******                  ****    ##.###      $#.##             $#.##        $##.##                    $#.##                     #.##%                    ***                     ***              #.##%              ***                ***  ****
     *########    ********** - ***       ****        ******.*** ***   ###.###    $###.##            -$#.##     $#####.##                 -$###.##                    -#.##%              -$####.##                 -##.##%             ##.##%        $#####.##            $###.##  ****
         #####  ****** ###(*) ****        ***    **** ** *** ******  ####.###     $##.##            -$#.##     $#####.##                 -$###.##                    -#.##%              +$####.##                 +##.##%             ##.##%        $#####.##             $##.##   ***
         #####  ****** ###(*) ****  #####*###  ******** ****** ####   ###.###    $###.##            -$#.##     $#####.##                  -$##.##                    -#.##%               +$###.##                  +#.##%             ##.##%        $#####.##            $###.##   ***
         #####  ****** ###(*) ****       ****      ******.*** *****    ##.###    $###.##            -$#.##     $#####.##                 -$###.##                    -#.##%              -$####.##                 -##.##%              #.##%        $#####.##            $###.##   ***
         #####  ****** ###(*) ****      *****  **** **** *** *** **  ####.###     $##.##            -$#.##     $#####.##                       --                        --              +$####.##                 +##.##%             ##.##%        $#####.##             $##.##   ***
```

### Return Schema

#### Balance Info
| Column Name               |
|---------------------------|
| Account Number            |
| Account Name              |
| Symbol                    |
| Description               |
| Quantity                  |
| Last Price                |
| Last Price Change         |
| Current Value             |
| Today's Gain/Loss Dollar  |
| Today's Gain/Loss Percent |
| Total Gain/Loss Dollar    |
| Total Gain/Loss Percent   |
| Percent Of Account        |
| Cost Basis                |
| Total Average Cost Basis  |
| Type                      |

## RoundPoint

[RoundPoint Mortgage](https://www.roundpointmortgage.com/)

### About

This is a Selenium driver that logs in using provided credentials, navigates 2FA, navigates to the detail account info
from the landing page for a mortgage serviced by Roundpoint Mortgage.

> ✔️ Driver supports handling of 2FA

### Example Usage

#### CLI
```shell
bank-scrape roundpoint $LOGIN_USER $LOGIN_PASS
```
#### API
```python
from bank_scrapers.scrapers.roundpoint.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```

#### Example 2FA Workflow
```console
>>> # Example 2FA workflow
>>> # TBD
```

#### Example Result
```
  Balance
 #####.##
Monthly Payment Amount Actual Due Date Next Draft Date
                ###.##   **** ##, ####   **** ##, ####
```

### Return Schema

#### Balance Info
| Column Name |
|-------------|
| Balance     |

#### Payment Info
| Column Name            |
|------------------------|
| Monthly Payment Amount |
| Actual Due Date        |
| Next Draft Date        |

## SMBC Prestia

[Sumitomo Mitsui Banking Corporation PRESTIA](https://www.smbctb.co.jp)

### About

This is a Selenium driver that logs in using provided credentials, navigates to the detail account info and scrapes
account info for a member account of SMBC Prestia.

> ❗️Driver does NOT currently support MFA

### Example Usage

#### CLI
```shell
bank-scrape smbc-prestia $LOGIN_USER $LOGIN_PASS
```

#### API
```python
from bank_scrapers.scrapers.smbc_prestia.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```

#### Example Result
```
Account Number  Available Amount
       #######           #######
      ########                 #
```

### Return Schema

#### Balance Info
| Column Name      |
|------------------|
| Account Number   |
| Available Amount |

## UHFCU

[University of Hawaii Federal Credit Union](https://www.uhfcu.com//)

### About

This is a Selenium driver that logs in using provided credentials, navigates 2FA, navigates to the detail account info
from the landing page for UHFCU account. It will also navigate to the credit card management system used by UHFCU and 
pull info for each credit card on the dashboard

> ✔️ Driver supports handling of 2FA

> 🚦 This driver acts slightly differently than the others: it will create 1 table in the return list per account in the
> user's dashboard. Said differently, **this driver does not produce a static amount of tables**

### Example Usage

#### CLI
```shell
bank-scrape uhfcu $LOGIN_USER $LOGIN_PASS
```

#### API
```python
from bank_scrapers.scrapers.uhfcu.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
  print(t.to_string())
```

#### Example 2FA Workflow
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
0: #********#@#####.###
1: ###-***-**##
Please select one: {user_choose_2fa_option}
Enter 2FA Code: {user_enters_2fa_code}
```

#### Example Result
```
Account Type               Account Desc Available Current Balance
     *******  **** ***** - *** ##-*####    $##.##          $##.##
Account Type               Account Desc  Available Current Balance
    ********  **** ***** - *** ##-*####  $#,###.##       $#,###.##
Current Balance Pending Balance Statement Balance Available Credit Last Payment as of *** ##, #### Total Minimum Due Payment Due Date                Last Login
          $#.##           $#.##             $#.##       $##,###.##                          $##.##             $#.##     *** ##, ####  *** ##, ####, #:##:## **
```

### Return Schema

#### Shared Accounts Info
| Column Name               |
|---------------------------|
| Account Type              |
| Account Desc              |
| Available                 |
| Current Balance           |

#### Loan Accounts Info
| Column Name                       |
|-----------------------------------|
| Current Balance                   |
| Pending Balance                   |
| Statement Balance                 |
| Available Credit                  |
| Last Payment as of *MMM DD, YYYY* |
| Total Minimum Due                 |
| Payment Due Date                  |
| Last Login                        |

## Vanguard

[The Vanguard Group](https://investor.vanguard.com/)

> ️✔️ This driver will pull holdings info for all Vanguard accounts for the account holder, including general brokerage
> accounts

### About

This is a Selenium driver that logs in using provided credentials, navigates 2FA, navigates to the detail account info
in the Downloads Center from the landing page.

Instead of scraping the user's account info from the page, this driver will navigate to the user's positions summary and
download the accounts info provided by Vanguard using a folder of the user's choice

> ➖️ Driver has limited support for 2FA (only supports mobile app touch authentication)

### Example Usage

#### CLI
```shell
bank-scrape vanguard $LOGIN_USER $LOGIN_PASS
```

> 💡 The CLI backend handles the creation of a tmp directory in the user's home directory by default. The API doesn't 
> have this functionality

#### API
```python
from bank_scrapers.scrapers.vanguard.driver import get_accounts_info

tables = get_accounts_info(username="{username}", password="{password}", tmp_dir="~/temp/")
for t in tables:
  print(t.to_string())
```
> ❗️**NOTE** `tmp_dir` MUST be empty for this function to work

#### Example 2FA Workflow
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
Waiting for 2FA...
```

#### Example Result
```
Account Number    Investment Name             Symbol    Shares   Share Price  Total Value
      ########    ***** **** ***  *** ** *    ***       ##.###   ##.####      ####.##
      ########    ******** ***                ****      ##.###   ##.####      ####.##
      ########    **** ********* *** ** *     ****      #.###    ###.####     ###.##
      ########    ******** **** ** * ***      ***       #.###    ##.####      ##.##
      ########    ********* ****              ****      #.###    ###.####     ###.##
```

### Return Schema

Provides int-ified values for each of the columns.

#### Balance Info
| Column Name      |
|------------------|
| Account Number   |
| Investment Name  |
| Symbol           |
| Shares           |
| Share Price      |
| Total Value      |

## Zillow

[Zillow](https://www.zillow.com/)

### About

This is a Selenium driver that finds a property's Zestimate from a user-provided url suffix (the part after 
`https://www.zillow.com/homedetails/`).

### Example Usage

#### CLI
```shell
bank-scrape zillow $URL_SUFFIX_FOR_PROPERTY
```
> 💡 The suffix of the Zillow URL (the part after 'homedetails'. Note that you only need to provide the part that ends 
> with "zpid"
 
> 💡 For example, this is a valid suffix argument (provided `#` was replaced by actual digits): `########_zpid`

#### API
```python
from bank_scrapers.scrapers.zillow.driver import get_accounts_info

tables = get_accounts_info(
  suffix="{house_num}-{street_name}-{street_type}-{city}-{state_code}-{5_digit_zip}/########_zpid")
for t in tables:
  print(t.to_string())
```

#### Example Result
```
  zestimate
0  $###,###
```

### Return Schema

#### Balance Info
| Column Name |
|-------------|
| zestimate   |

# API Wrappers

These are wrappers written around API endpoints provided by providers and are generally purposed around making these
processes of getting accounts info cohesive across this library. 

## Kraken

[Kraken](https://www.kraken.com/)

### About

This is an API wrapper for pulling Kraken account holdings based on Kraken's 
[documentation](https://docs.kraken.com/rest).

The main purpose of this wrapper is to provide an even simpler interface for pulling account holdings and to align the 
data provided by Kraken with the rest of the financial data pulled by this package. 

### Example Usage

#### CLI
```shell
bank-scrape kraken $API_KEY $SECRET_KEY
```

#### API
```python
from bank_scrapers.api_wrappers.kraken.driver import get_accounts_info

tables = get_accounts_info(
  api_key="*****************/**************************************",
  api_sec="********+*************************+****+********//******************/**************+**==",
)
for t in tables:
  print(t.to_string())
```

#### Example Result
```
symbol      quantity
  ****  #.##########
  ****     #.#######
  ****        #.####
  ****  #.##########
```

### Return Schema

#### Balance Info
| Column Name |
|-------------|
| symbol      |
| quantity    |

# Disclaimer

The intended purpose of this code is purely academic in nature, and it IS NOT intended to be used for any real life
production use, nefarious or otherwise.

Usage of this code is potentially against your bank's terms of service and could result in you or your IP getting
flagged, listed, or blocked as bad actors. I don't take any responsibility for any effects this code may have on your
bank accounts or your relationships with your banking institutions.

Please don't try to learn anything about me or my life based on the banks that I've arbitrarily decided to write
drivers for. 