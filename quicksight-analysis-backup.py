'''the below code is designed to run daily and backup modified analysis to the shared folder 'backup'

to backup or create an analysis through the API you need the Template ARN, Datasets ARN, Name and unique ID
STEP1: use list analysis to find analysis updated today, 
STEP2: use describe analysis to get the analysis arn, dataset arn
STEP3: use create template to create an template and get the template arn
STEP4: use these values in source entity of create analysis to replicate the analysis 
STEP5: apply test backup folder membership to store in test-backup shared folder 

naming convention : backup-{analysis name}-{backup date}  ***** delete-old-backups.py wil be used to keep only last 3 backups'''

# Create a client for STS to get AWS Account ID


def get_aws_account_id(sts_client):
    try:
        identity = sts_client.get_caller_identity()
        return identity['Account']
    except ClientError as e:
        print(f"Error getting AWS account ID: {e}")
        return None


def list_analyses_updated_today(aws_account_id, client): 
    analyses = []
    next_token = None
    today = datetime.datetime.now().date()

    try:
        while True:
            if next_token:
                response = client.list_analyses(
                    AwsAccountId=aws_account_id,
                    MaxResults=100, #max allowed per request
                    NextToken=next_token
                )
            else:
                response = client.list_analyses(
                    AwsAccountId=aws_account_id,
                    MaxResults=100
                )
            
            analyses.extend(response.get('AnalysisSummaryList', []))
            next_token = response.get('NextToken')
            if not next_token:
                break  
    
        # Filter analyses that were updated today and are not deleted           
        updated_today_analyses = [
            analysis for analysis in analyses if analysis['LastUpdatedTime'].date() == today and analysis['Status'] != 'DELETED'
        ]

        return updated_today_analyses
    except ClientError as e:
        print(f"Error listing analyses: {e}")
        return None

def describe_analysis(analysis_id, aws_account_id, client):
    try:
        #Get ARN, datasets ARNs
        response = client.describe_analysis(
            AwsAccountId=aws_account_id,
            AnalysisId=analysis_id
        )

        analysis_arn = response['Analysis']['Arn']
        datasets = response['Analysis']['DataSetArns']

        return analysis_arn, datasets
    except ClientError as e:
        print(f"Error describing analysis {analysis_id}: {e}")
        return None, None


def create_template_from_analysis(analysis_id, analysis_name, analysis_arn, datasets, aws_account_id, client):
    try:
        #create template and get templateARN
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        template_name = f"{analysis_name}-temp-{current_date}"
        template_id = re.sub(r'\W+', '-', f"{analysis_name}-{current_date}")# Replace invalid characters

        # Check if template is existing
        try:
            existing_template = client.describe_template(
                AwsAccountId=aws_account_id,
                TemplateId=template_id
            )
            print(f"Template '{template_name}' already exists. Skipping creation.")
            return existing_template['Template']['Arn'], None
        except client.exceptions.ResourceNotFoundException:
            pass

        dataset_references = [
            {
                'DataSetPlaceholder': f"{analysis_name}-{i+1}-{current_date}",
                'DataSetArn': dataset_arn
            }
            for i, dataset_arn in enumerate(datasets)
        ]

        response = client.create_template(
            AwsAccountId=aws_account_id,
            TemplateId=template_id,
            Name=template_name,
            SourceEntity={
                'SourceAnalysis': {
                    'Arn': analysis_arn,
                    'DataSetReferences': dataset_references
                }
            },
            Permissions=[
                {
                    'Principal': f'arn:aws:quicksight:us-east-1:{aws_account_id}:group/Admins', #ENTER/REPLACE YOUR GROUP/ADMIN GROUP PRINCIPAL ARN
                    'Actions': [
                        'quicksight:DescribeTemplate',
                        'quicksight:UpdateTemplatePermissions',
                        'quicksight:DeleteTemplate',
                        'quicksight:DescribeTemplatePermissions',
                        'quicksight:UpdateTemplate'
                    ]
                }
            ],
            VersionDescription=f'Template for {analysis_name} created on {current_date}'
        )

        template_arn = response['Arn']
        print(f"Template created with ARN: {template_arn}")
        return template_arn, dataset_references
    except ClientError as e:
        print(f"Error creating template from analysis {analysis_id}: {e}")
        return None, None


def create_analysis_from_template(analysis_name, template_arn, dataset_references, aws_account_id, client):
    try:
        #use TemplateARN, DatasentARN, AnalysisARN within SourceEntity to create analysis
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        analysis_id = f'backup-{analysis_name}-{current_date}'
        analysis_name_formatted = f'backup-{analysis_name}-{current_date}'
        
        response = client.create_analysis(
            AwsAccountId=aws_account_id,
            AnalysisId=analysis_id,
            Name=analysis_name_formatted,
            SourceEntity={
                'SourceTemplate': {
                    'Arn': template_arn,
                    'DataSetReferences': dataset_references
                }
            },
            Permissions=[
                {
                    'Principal': f'arn:aws:quicksight:us-east-1:{aws_account_id}:group/default/MIQ-Admins',
                    'Actions': [
                        'quicksight:RestoreAnalysis',
                        'quicksight:DeleteAnalysis',
                        'quicksight:QueryAnalysis',
                        'quicksight:DescribeAnalysis',
                        'quicksight:UpdateAnalysisPermissions',
                        'quicksight:DescribeAnalysisPermissions',
                        'quicksight:UpdateAnalysis'
                    ]
                }
            ]
        )
        
        analysis_arn = response['Arn']
        print(f"Analysis '{analysis_name_formatted}' created with ARN: {analysis_arn}")
        
        return analysis_id
    except ClientError as e:
        print(f"Error creating analysis: {e}")
        return None

def assign_analysis_to_folder(analysis_id, folder_id, aws_account_id, client):
    try:
        response = client.create_folder_membership(
            AwsAccountId=aws_account_id,
            FolderId=folder_id,
            MemberId=analysis_id,
            MemberType='ANALYSIS'
        )
        print(f"Analysis '{analysis_id}' added to folder '{folder_id}'.")
    except ClientError as e:
        print(f"Error assigning analysis to folder: {e}")


def main():
    # Set up argument parsing for folder_id
    parser = argparse.ArgumentParser(description="Backup QuickSight analyses.")
    parser.add_argument('--profile', type=str, default='dev', help='AWS profile to use')
    parser.add_argument('--folder_id', type=str, required=True, help='Folder ID in QuickSight')

    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile)
    sts_client = session.client('sts')
    client = session.client('quicksight')
    folder_id = args.folder_id
    aws_account_id = get_aws_account_id(sts_client)

    if aws_account_id:
        updated_analyses = list_analyses_updated_today(aws_account_id, client)

        if not updated_analyses:
            print("No analyses updated today.")
            return

        for analysis in updated_analyses:
            analysis_id = analysis['AnalysisId']
            analysis_name = re.sub(r'\W+', '-', analysis['Name'])

            analysis_arn, datasets = describe_analysis(analysis_id, aws_account_id, client)

            if analysis_arn and datasets:
                template_arn, dataset_references = create_template_from_analysis(analysis_id, analysis_name, analysis_arn, datasets, aws_account_id, client)

                if template_arn and dataset_references is None:
                    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                dataset_references = [
                    {
                        'DataSetPlaceholder': f"{analysis_name}-{i+1}-{current_date}",
                        'DataSetArn': dataset_arn
                    }
                    for i, dataset_arn in enumerate(datasets)
                ]

            if template_arn:
                # Wait for template to be fully created
                time.sleep(30)
                new_analysis_id = create_analysis_from_template(analysis_name, template_arn, dataset_references, aws_account_id, client)
                
                if new_analysis_id:
                    assign_analysis_to_folder(new_analysis_id, folder_id, aws_account_id, client)
            else:
                print(f"Skipping analysis {analysis_name} due to missing data.")
    else:
        print("Could not retrieve AWS account ID. Exiting.")

if __name__ == "__main__":
    main()

