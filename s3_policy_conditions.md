### Allow Specific Federated User to Put Objects:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::abc/*",
            "Condition": {
                "StringEquals": {
                    "aws:username": "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/YourRoleName/federated-user-name"
                }
            }
        }
    ]
}
```

### Allow Specific Federated User Based on IP Address:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::abc/*",
            "Condition": {
                "IpAddress": {
                    "aws:SourceIp": "x.x.x.x" 
                },
                "StringEquals": {
                    "aws:username": "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/YourRoleName/federated-user-name"
                }
            }
        }
    ]
}
```

### Allow Specific Federated User Based on MFA:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::abc/*",
            "Condition": {
                "Bool": {
                    "aws:MultiFactorAuthPresent": "true"
                },
                "StringEquals": {
                    "aws:username": "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/YourRoleName/federated-user-name"
                }
            }
        }
    ]
}
```

### For multiple roles and a user
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::abc/*",
            "Condition": {
                "StringEquals": {
                    "aws:username": [
                        "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/Role1",
                        "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/Role2",
                        "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/Role3",
                        "arn:aws:sts::YOUR_ACCOUNT_ID:assumed-role/YourRoleName/federated-user-name",
                        "xyz"
                    ]
                }
            }
        }
    ]
}

```
