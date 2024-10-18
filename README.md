# do-python-automation-scripts
Automation scripts to run queries for data operations


## QuickSight API Automation Scripts 

This repository contains Python scripts to automate AWS QuickSight processes, specifically for creating backups of analyses based on daily updates.

## Scripts Overview

- **`create-folder-grant-permissions.py`**: 
  This script is used to create a shared folder in AWS QuickSight and grant specific permissions to a group of users. It can be used to organize resources and manage access control efficiently.

- **`quicksight-analysis-backup.py`**: 
  This script automates the backup process for AWS QuickSight analyses. It checks for any analyses that have been updated on the current day, retrieves the necessary dataset ARNs and analysis ARNs, and creates templates from them. The templates are used to create new analysis backups within the `backup` folder. (Make sure to enter your group ARN as mentioned in the code)

- **`delete-old-backups.py`**: 
  This script helps manage storage by keeping only the latest 3 backups or versions of an analysis. It automatically deletes older backups beyond the 3 most recent ones, ensuring efficient use of resources while maintaining important versions.

## How to Use
1. refer to comments in the code in upper case to make changes or replicate on your end
2. install the required libraries using requirements.txt by exceuting command    ``pip install -r requirements.txt``

   a. to create a folder and grant permissions to a group exceute   ``python create-folder-grant-permissions.py --profile <enter profile_name> --folder_id <enter folder_name> --group_name <enter group_name>``

   b. to run the backup job exceute   ``python quicksight-analysis-backup.py --profile <enter profile_name> --folder_id <enter folder_name>``

   c. to keep only the top 3 backups for an analysis exceute   ``python delete-old-backups.py --profile <enter profile_name> --folder_id <enter folder_name>``
