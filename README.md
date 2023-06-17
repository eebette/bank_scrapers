# Table of Contents

- [Introduction](#introduction)
- [Drivers](#drivers)
  - [BECU](#becu)
    - [About](#about)
    - [Example Usage](#example-usage)
    - [Return Schema](#return-schema)
  - [Chase](#chase)
    - [About](#about-1)
    - [Example Usage](#example-usage-1)
    - [Return Schema](#return-schema-1)

# Introduction

`bank_scrapers` is a library containing drivers for scraping account information from various financial websites. 

Since most traditional financial institutions don't provide an API for accessing one's account data, most of these
drivers utilize `Selenium` to impersonate the user using the provided credentials.

# Drivers

## BECU

[Boeing Enterprises Credit Union](https://www.becu.org/)

### About

This is a Selenium driver that logs in using provided credentials and reads account info from the landing page.

> ❗️Driver does NOT currently support MFA
> 
### Example Usage

```python
from scrapers.becu.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
```
      Account  YTD Interest  Current Balance  Available Balance
0  ##########          #.##          ####.##            ####.##
1  ##########         ##.##         #####.##           #####.##
2  ##########        ###.##         #####.##           #####.##
   Account  Current Balance  Available Credit
0     ####           ###.##           #####.#
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

### Example Usage

```python
from scrapers.chase.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
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
```
  Current balance Pending charges Available credit Total credit limit Next closing date Balance on last statement Remaining statement balance Payments are due on the
0         ####.##          ###.##         #####.##           #####.##             ####              ####.#######                     ####.##                      #.
   Last payment Minimum payment Automatic Payments
0  ####.#######      ##.#######                   
  Points available
0           ######
  Cash advance balance Available for cash advance Cash advance limit
0                 #.##                    ####.##            ####.##
  Purchase APR Cash advance APR
0        ##.##            ##.##
  Program details
0            
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

```python
from scrapers.fidelity_netbenefits.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}", tmp_dir="~/tmp")
for t in tables:
    print(t.to_string())
```
> ❗️**NOTE** `tmp_dir` MUST be empty for this function to work
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
0: Use *...*@*****.***
1: Use *...*@**.**
2: Use *...*@******.***
Please select one: {user_choose_2fa_option}
Enter 2FA Code: {user_enters_2fa_code}
```
```
  Account Number        Account Name     Symbol           Description  Quantity Last Price Last Price Change Current Value Today's Gain/Loss Dollar Today's Gain/Loss Percent Total Gain/Loss Dollar Total Gain/Loss Percent Percent Of Account Cost Basis Total Average Cost Basis  Type
#      *########    ********** - ***    *******                  ****    ##.###      $#.##             $#.##        $##.##                    $#.##                     #.##%                    ***                     ***              #.##%              ***                ***  ****
#      *########    ********** - ***       ****        ******.*** ***   ###.###    $###.##            -$#.##     $#####.##                 -$###.##                    -#.##%              -$####.##                 -##.##%             ##.##%        $#####.##            $###.##  ****
#          #####  ****** ###(*) ****        ***    **** ** *** ******  ####.###     $##.##            -$#.##     $#####.##                 -$###.##                    -#.##%              +$####.##                 +##.##%             ##.##%        $#####.##             $##.##   ***
#          #####  ****** ###(*) ****  #####*###  ******** ****** ####   ###.###    $###.##            -$#.##     $#####.##                  -$##.##                    -#.##%               +$###.##                  +#.##%             ##.##%        $#####.##            $###.##   ***
#          #####  ****** ###(*) ****       ****      ******.*** *****    ##.###    $###.##            -$#.##     $#####.##                 -$###.##                    -#.##%              -$####.##                 -##.##%              #.##%        $#####.##            $###.##   ***
#          #####  ****** ###(*) ****      *****  **** **** *** *** **  ####.###     $##.##            -$#.##     $#####.##                       --                        --              +$####.##                 +##.##%             ##.##%        $#####.##             $##.##   ***
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

```python
from scrapers.roundpoint.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
```console
>>> # Example 2FA workflow
>>> # TBD
```
```
    Balance
0  #####.##
  Monthly Payment Amount Actual Due Date Next Draft Date
0                 ###.##   **** ##, ####   **** ##, ####
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

```python
from scrapers.smbc_prestia.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
```
   Account Number  Available Amount
0         #######           #######
1        ########                 #
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

```python
from scrapers.uhfcu.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}")
for t in tables:
    print(t.to_string())
```
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
0: #********#@#####.###
1: ###-***-**##
Please select one: {user_choose_2fa_option}
Enter 2FA Code: {user_enters_2fa_code}
```
```
  Account Type               Account Desc Available Current Balance
#      *******  **** ***** - *** ##-*####    $##.##          $##.##
  Account Type               Account Desc  Available Current Balance
#     ********  **** ***** - *** ##-*####  $#,###.##       $#,###.##
  Current Balance Pending Balance Statement Balance Available Credit Last Payment as of *** ##, #### Total Minimum Due Payment Due Date                Last Login
#           $#.##           $#.##             $#.##       $##,###.##                          $##.##             $#.##     *** ##, ####  *** ##, ####, #:##:## **
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

```python
from scrapers.vanguard.driver import get_accounts_info
tables = get_accounts_info(username="{username}", password="{password}", tmp_dir="~/temp/")
for t in tables:
    print(t.to_string())
```
> ❗️**NOTE** `tmp_dir` MUST be empty for this function to work
```console
>>> # Example 2FA workflow
>>> tables = get_accounts_info(username="{username}", password="{password}")
Waiting for 2FA...
```
```
    Account Number    Investment Name             Symbol    Shares   Share Price  Total Value
#         ########    ***** **** ***  *** ** *    ***       ##.###   ##.####      ####.##
#         ########    ******** ***                ****      ##.###   ##.####      ####.##
#         ########    **** ********* *** ** *     ****      #.###    ###.####     ###.##
#         ########    ******** **** ** * ***      ***       #.###    ##.####      ##.##
#         ########    ********* ****              ****      #.###    ###.####     ###.##
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