wget -qO - https://packages.irods.org/irods-signing-key.asc | sudo apt-key add -
echo "deb [arch=amd64] https://packages.irods.org/apt/ xenial main" | sudo tee /etc/apt/sources.list.d/renci-irods.list
sudo apt-get update
sudo apt -y install aptitude irods-runtime=4.2.6 irods-icommands=4.2.6
sudo aptitude hold irods-runtime irods-icommands
