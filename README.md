# destiny2-reset-tracker
Get notified for weekly rotations

## Setup Instructions

### Step 1: Create a Bungie Application
1. go to [Bungie Companion Application](https://www.bungie.net/en/Application) and create a new application.
2. Head to your Application tab and get the following credentials
    - API keys
    - oAuth Authorization URL
    - OAuth client_id
3. Copy and assing them in a `.env` file.

### Step 2: Configure environment variables


1. Add the following variable to your `.env` file. Bungie's API can  be difficult to navigate for live milestones, so a static variable is used for comparison after querying the database:

```py
ACTIVITIES={
    "3181387331":"Last Wish",
    "2712317338":"Garden of Salvation",
    "541780856":"Deep Stone Crypt",
    "2136320298":"Vow of the Disciple",
    "1888320892":"Vault of Glass",
    "292102995":"King's Fall",
    "3699252268":"Root of Nightmares",
    "540415767":"Crota's End",
    "4196566271":"Salvation's Edge",
    "3921784328":"Warlord's Ruin",
    "1742973996":"The Shattered Throne",
    "422102671":"Pit of Heresy",
    "2032830539":"Sundered Doctrine",
    "1080663862":"Vesper's Host",
    "3618845105":"Duality",
    "478604913":"Prophecy",
    "390471874":"Ghosts of the Deep",
    "526718853":"Spire of the Watcher",
    "1112917203":"Grasp of Avarice",
    "2029743966":"Nightfall"
}
```
2. go to your google account and create an app password and add 
`EMAIL = "your gmail"` and `PASSWORD = "app password"` making sure to delete the spaces from your 16 char generated password.
3. Add `NUMBER="your number"` and `CARRIER="your carrier gateway"` to your environment variables


### Step 3: Install dependencies
Install the required python packages `pip install -r requirements.txt` 
