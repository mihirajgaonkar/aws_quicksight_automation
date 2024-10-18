'''
The following code is used to create shared folders in quicksight and grant permissions to a specific group
STEP1 : get the account id and ARN , group name, folder name which will be the same as id for simplicity and ease of search and maintainance
STEP2 : create shared folder and provide creator permissions
STEP 3 : assign group and provide permissions
'''
namespace = 'default' #CHANGE NAMESPACE IF YOUR CURRENT NAMESPACE IN ARN'S IS NOT DEFAULT 

def get_aws_account_details(sts_client):
    try:
        identity = sts_client.get_caller_identity()
        aws_account_id = identity['Account']
        arn = identity['Arn']
        return aws_account_id, arn
    except Exception as e:
        print(f"Error retrieving AWS account details: {e}")
        return None, None

def create_folder(folder_name, aws_account_id, arn, client):
    try:
        # Initial permissions for the folder required
        permissions = [
            {
                'Principal': arn,  
                'Actions': [
                    'quicksight:CreateFolder',
                    'quicksight:DescribeFolder',
                    'quicksight:UpdateFolder',
                    'quicksight:DeleteFolder',
                    'quicksight:CreateFolderMembership',
                    'quicksight:DeleteFolderMembership',
                    'quicksight:DescribeFolderPermissions',
                    'quicksight:UpdateFolderPermissions'
                ]
            }
        ]

        response = client.create_folder(
            AwsAccountId=aws_account_id,
            FolderId=folder_name.lower().replace(' ', '-'),  # Folder ID must be lowercase and without spaces
            Name=folder_name,
            Permissions=permissions  
        )
        folder_arn = response['Arn']  # Get the folder ARN
        print(f"Folder '{folder_name}' created with ARN: {folder_arn}")
        return folder_arn
    except ClientError as e:
        print(f"Error creating folder: {e}")
        return None


def grant_permissions(aws_account_id, group_name, folder_arn, client):
    try:
        # List the users in the group
        group_users = client.list_group_memberships(
            AwsAccountId=aws_account_id,
            Namespace=namespace,
            GroupName=group_name
        )

        # append user ARNS to list 'principals' and grant permissions to each user
        principals = []
        for user in group_users['GroupMemberList']:
            principals.append(user['Arn'])

        
        permissions = [
            {
                'Principal': principal,
                'Actions': [
                    'quicksight:CreateFolder',
                    'quicksight:DescribeFolder',
                    'quicksight:UpdateFolder',
                    'quicksight:DeleteFolder',
                    'quicksight:CreateFolderMembership',
                    'quicksight:DeleteFolderMembership',
                    'quicksight:DescribeFolderPermissions',
                    'quicksight:UpdateFolderPermissions'
                ]
            } for principal in principals
        ]

        
        response = client.update_folder_permissions(
            AwsAccountId=aws_account_id,
            FolderId=folder_arn.split('/')[-1],  # Extract the FolderId from the ARN
            GrantPermissions=permissions
        )

        print(f"Permissions granted to users in group '{group_name}'.")
    except ClientError as e:
        print(f"Error granting permissions: {e}")



def main():
    parser = argparse.ArgumentParser(description='Grant permissions to a QuickSight folder')
    parser.add_argument('--profile', type=str, default='dev', help='AWS profile to use') 
    parser.add_argument('--folder_id', required=True, help='The name of the folder to grant permissions to') #folder_id is same as folder_name for simplicity easier to search and track
    parser.add_argument('--group_name', required=True, help='The name of the group to grant permissions to')


    args = parser.parse_args()
    
    session = boto3.Session(profile_name=args.profile)
    sts_client = session.client('sts')
    client = session.client('quicksight')
    folder_name = args.folder_id
    group_name = args.group_name
    
    aws_account_id, arn = get_aws_account_details(sts_client)
    
    if aws_account_id and arn:
        print(f"Retrieved AWS Account ID: {aws_account_id}")
        print(f"Retrieved ARN: {arn}")
        
        create_folder(folder_name, aws_account_id, arn, client)
        grant_permissions(folder_name, group_name, client)
    else:
        print("Failed to retrieve AWS account details, cannot proceed with granting permissions.")

if __name__ == "__main__":
    main()
