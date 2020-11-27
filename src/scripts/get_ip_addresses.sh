aws2 ec2 describe-instances --query 'Reservations[*].Instances[*].[PublicIpAddress]' --filters Name=instance-state-name,Values=running --output text | sort | sed 's/.*/    \0:/g'
