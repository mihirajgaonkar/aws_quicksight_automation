'''this code is used to keep only the last 3 copies of backed up analyses, the code deletes analyses based on back up date and is expected to run after quicksight-analysis-backup.py
STEP1: list files in the shared folder using 'list_folder_members()'
STEP2: extract the date from the title from the analysis, split title into analysis_id, name, date, order by date and sort top 3 based on date
STEP4: delete all other analysis
'''


def get_aws_account_id(sts_client):
    try:
        identity = sts_client.get_caller_identity()
        aws_account_id = identity['Account']
        return aws_account_id
    except ClientError as e:
        print(f"Error retrieving AWS account ID: {e}")
        return None


def list_analyses_in_folder(aws_account_id, folder_id, client):
    try:
        response = client.list_folder_members(
            AwsAccountId=aws_account_id,
            FolderId=folder_id
        )

        folder_members = response.get('FolderMemberList', [])
        analyses = [member for member in folder_members]
        return analyses

    except ClientError as e:
        print(f"Error listing analyses in folder: {e}")
        return []


def delete_analysis(aws_account_id, analysis_id, client):
    try:
        client.delete_analysis(
            AwsAccountId=aws_account_id,
            AnalysisId=analysis_id
        )
        print(f"Deleted analysis: {analysis_id}")
    except ClientError as e:
        print(f"Error deleting analysis {analysis_id}: {e}")

# get only the latest top 3 backups for an analysis
def keep_top_3_backups(aws_account_id, folder_id, client):
    analyses = list_analyses_in_folder(aws_account_id, folder_id, client)

    analyses_with_names = []
    for analysis in analyses:
        analysis_id = analysis['MemberId']
        temp_analysis_name = analysis_id.split("-") 
        analysis_name = temp_analysis_name[1] 
        analysis_date = analysis_id[-10:]
        analyses_with_names.append({
                'analysis_id': analysis_id,
                'analysis_name': analysis_name,
                'analysis_date' : analysis_date
            })
            
    analyses_with_names_df = pd.DataFrame(analyses_with_names)
    df_sorted = analyses_with_names_df.sort_values(by=['analysis_name', 'analysis_date'], ascending=[True, False])
    top_3_per_group = df_sorted.groupby('analysis_name').head(3)
    analysis_ids_in_top_3 = top_3_per_group['analysis_id'].tolist()
    analyses_to_delete = analyses_with_names_df[~analyses_with_names_df['analysis_id'].isin(analysis_ids_in_top_3)]

    if analyses_to_delete.empty:
        print("There are fewer than 3 analyses, no need to delete any.")
    else:
        for analysis in analyses_to_delete.itertuples():
            delete_analysis(aws_account_id, analysis.analysis_id)

def main():
    # retrieve folder_id from the command line
    parser = argparse.ArgumentParser(description='Delete old analysis backups and keep the top 3 based on date.')
    parser.add_argument('--profile', type=str, default='dev', help='AWS profile to use') 
    parser.add_argument('--folder_id', required=True, help='The ID of the folder to manage backups')
    
    
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile)
    sts_client = session.client('sts')
    client = session.client('quicksight')
    folder_id = args.folder_id

    aws_account_id = get_aws_account_id(sts_client)
    
    if aws_account_id:
        print(f"Retrieved AWS Account ID: {aws_account_id}")
        keep_top_3_backups(aws_account_id, folder_id, client)
    else:
        print("Failed to retrieve AWS account details, cannot proceed.")

if __name__ == "__main__":
    main()
