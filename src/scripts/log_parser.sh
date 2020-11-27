echo "Input argument: log file"
grep -oP "ERROR    Exception occurred while fetching .*" $1 | sed -E 's/.*web\/([0-9]{14})\/(.*)/\1∞\2/g' | sort > $1_errors.csv
grep -oP  "WARNING  404: http://web.archive.org/\K(.*)" $1 | sed -E 's/.*web\/([0-9]{14})\/(.*)/\1∞\2/g' | sort > $1_notfound.csv
grep -oP  "ERROR    403: http://web.archive.org/\K(.*)" $1 | sed -E 's/.*web\/([0-9]{14})\/(.*)/\1∞\2/g' | sort >> $1_httpErr.csv
grep -oP  "ERROR    503: http://web.archive.org/\K(.*)" $1 | sed -E 's/.*web\/([0-9]{14})\/(.*)/\1∞\2/g' | sort >> $1_httpErr.csv
grep -oP "INFO     Successfully uploaded .*" $1 | sed -E 's/.*web\/([0-9]{14})\/(.*)/\1∞\2/g' | sort > $1_success.csv
