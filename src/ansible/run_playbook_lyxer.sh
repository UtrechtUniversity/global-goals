#!/bin/bash
installed=$(dpkg-query -W -f='${Status}' ansible 2>/dev/null | grep -c "ok installed")
cver=$(dpkg -s ansible | grep '^Version:' | cut -b 10-12 2>/dev/null)
rver="2.9"

if [ $installed -eq 0 ] || ! [ "$(printf '%s\n' "$rver" "$cver" | sort -V | head -n1)" = "$rver" ]
then
  echo "Installing latest version of package 'ansible'"
  sudo apt update
  sudo apt install software-properties-common
  sudo apt-add-repository --yes --update ppa:ansible/ansible
  sudo apt-get install ansible
fi

if test -f "VAULT_SECRET"; then
    ansible-playbook -i hosts --diff playbook_link_lyxer.yml --vault-password-file VAULT_SECRET $*
else
    ansible-playbook -i hosts --diff playbook_link_lyxer.yml --ask-vault-pass $*
fi
