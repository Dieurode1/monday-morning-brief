# AWS setup

`mmb-bedrock-policy.json` is the inline policy for the `mmb-bedrock` IAM user.
It allows calls to Kimi K3.1 through the US inference profile and nothing else.

Replace `<AWS_ACCOUNT_ID>` with your account number before attaching it.
The user's access key is stored locally with `aws configure --profile mmb-bedrock`, never in this repo.
