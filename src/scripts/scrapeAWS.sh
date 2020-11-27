aws2 s3 ls s3://975435234474-global-goals --recursive > downloaded.txt
sed -i -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} +[0-9]+ //g' downloaded.txt

