# Text Message History Formatter

This project processes and formats text message history exports from iMessage. It handles messages from various senders and formats them consistently for better readability and analysis.

## Features

- Processes iMessage exports into a structured format
- Normalizes phone numbers and maps them to contact names based on a configurable mapping
- Handles both phone numbers and email addresses for contacts (e.g., Phil's email)
- Preserves specific sender names (e.g., "Jess") while mapping others to their contact names
- Splits output into manageable chunks for better handling

## Environment Setup

1. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate txt-history
```

2. Important: If you have pyenv installed, you may need to temporarily disable it to ensure conda's Python is used:
```bash
pyenv global system
```

3. Verify you're using the correct Python:
```bash
which python  # Should point to your conda environment's Python
python --version  # Should show Python 3.11.x
```

## Command line

I want to be able to call:

    python3 format_txt_history_full.py -s 0.2 -d "2024-12-01"
    
with optional parameters:
   -s (max chunk size in mb)
   -d (date)
   -m (name, defulat: Phil)

## Input Data Format from immesage-exporter (sample)

```bash
Dec 17, 2024  4:31:51 PM
Jess
Ohh ok 16 mins at 425

Dec 17, 2024 10:14:08 PM (Read by Jess after 11 seconds)
apple@phil-g.com
I can take the night shift today and you can sleep through until ~7am if that works for you. If you’d rather do the night shift I need to get ready for bed now

Dec 17, 2024 10:15:02 PM (Read by them after 2 seconds)
Jess
Sure I can set an alarm for 7 but if she wakes up in the next little bit I’ll still be up

Dec 17, 2024 10:17:23 PM (Read by Jess after 5 seconds)
apple@phil-g.com
Ok message me when you’re laying down to sleep. Keep in mind that it may take me a bit longer than you to wake up from her crying depending on which sleep phase I am in, but I will hear it
```

## Output Dir Structure

DATETIME/
    - CHUNKS_CSV/
        CHUNK_1.csv
        CHUNK2.csv
        ...
    - CHUNKS_txt/
        CHUNK_1.txt
        CHUNK2.txt
        ...

## Output Data Format (sample)

### chunk_1.txt

```bash
Jess, Aug 30, 2024 10:42:49 PM, I totally forgot 

Jess, Aug 31, 2024 12:33:42 AM, Look outside 

Jess, Aug 31, 2024 12:33:46 AM, Go outside and look up 

Jess, Aug 31, 2024 12:33:59 AM, Quick 

Jess, Aug 31, 2024 12:34:49 AM, I’ve never in my life seen the northern lights this bright or this big or this magical lol 

Rhonda, Aug 31, 2024 11:29:50 AM, Oh shit. I would have liked that. 

Rhonda, Aug 31, 2024 11:30:34 AM, How’s packing?  If you need I can come by and watch her so you guys can get out of there 

Jess, Aug 31, 2024 11:36:21 AM, Omg that would be so helpful 

Jess, Aug 31, 2024 11:36:41 AM, She was up so much last night and is in a mood from all the hustle and bustle 
```

### chunk_1.csv

```bash
Jess,"Aug 30, 2024 10:42:49 PM","I totally forgot"
Jess,"Aug 31, 2024 12:33:42 AM","Look outside"
Jess,"Aug 31, 2024 12:33:46 AM","Go outside and look up"
Jess,"Aug 31, 2024 12:33:59 AM","Quick"
Jess,"Aug 31, 2024 12:34:49 AM","I’ve never in my life seen the northern lights this bright or this big or this magical lol"
Rhonda,"Aug 31, 2024 11:29:50 AM","Oh shit. I would have liked that."
Rhonda,"Aug 31, 2024 11:30:34 AM","How’s packing?  If you need I can come by and watch her so you guys can get out of there"
Jess,"Aug 31, 2024 11:36:21 AM","Omg that would be so helpful"
Jess,"Aug 31, 2024 11:36:41 AM","She was up so much last night and is in a mood from all the hustle and bustle"
