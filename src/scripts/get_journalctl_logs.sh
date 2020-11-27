IFS=$'\n'       # make newlines the only separator
set -f          # disable globbing
for p in $(cat < "$1"); do
  ssh -i ~/.ssh/global-goals.pem ubuntu@$p 'sudo journalctl -au globalgoals.service > log.txt'
  scp -i ~/.ssh/global-goals.pem ubuntu@$p:log.txt ./log$p.txt
done


