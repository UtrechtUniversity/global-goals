# Global Goals

This repository describes an approach to obtain historical hyperlinks among a given set of International Organizations (IOs).
The hyperlinks are retrieved from the oranizations' websites from 2012 up to 2019 via the Internet Archive.

This approach is further developed in the Crunchbase project.
For an improved and more generic version of the IA webscraping pipeline, check out the [ia-webscraping repository](https://github.com/UtrechtUniversity/ia-webscraping).


<!-- TABLE OF CONTENTS -->
## Table of Contents

- [Project Title](#global-goals)
  - [Table of Contents](#table-of-contents)
  - [About the Project](#about-the-project)
    - [License](#license)
    - [Attribution and academic use](#attribution-and-academic-use)
  - [Getting Started](#getting-started)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
  - [Usage](#local-usage)
  - [Ansible workflow](#ansible-workflow)
  - [Contact](#contact)

<!-- ABOUT THE PROJECT -->
## About the Project

**Date**: June 2022

**Researcher(s)**:

- Maya Bogers (m.j.bogers@uu.nl)

**Research Software Engineer(s)**:

- Jelle Treep (h.j.treep@uu.nl)
- Martine de Vos (m.g.devos@uu.nl)

<!-- Do not forget to also include the license in a separate file(LICENSE[.txt/.md]) and link it properly. -->
### License

The code in this project is released under [LICENSE.md](LICENSE).

### Attribution and academic use

The hyperlinks collected with the pipeline from this repository have been used in the following scientific publication:
Bogers, M et al. [_The impact of the Sustainable Development Goals on a network of 276 international organizations_](https://www.sciencedirect.com/science/article/pii/S0959378022001054)(2022)


<!-- GETTING STARTED -->
## Getting Started

Guide to get a local copy of this project up and running.
```
git clone https://github.com/UtrechtUniversity/global-goals.git
```


### Prerequisites

To install and run this project you need to have the following prerequisites installed.

- Ansible
- Python


<!-- USAGE -->
## Local Usage 

The project consists of four stages as listed below. In short: 
- get list of cdx records
- download html pages
- extract all hyperlinks 
- extract network hyperlinks.

If a fairly large amount of url's needs to be obtained, multiple servers should be used. 
These servers can be populated using Ansible, see [Ansible workflow](#ansible-workflow). In that case the workflow looks like:
> obtain cdx records -> split records -> setup AWS -> deploy to servers -> fetch logs -> obtain status (-> redo)

### Stage 1: Fetching CDX Records (cdx_record_fetcher)
A CDX Record is a record from the [CDX Api](https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server) of the Internet Archive. Such a record consists of an url_key and a timestamp. An example would be:
```
timestamp = 20180806145630
url_key = https://www.uu.nl/en/research/research-data-management
```
This would result in the following url: [https://web.archive.org/web/`20180806145630`/`https://www.uu.nl/en/research/research-data-management`](https://web.archive.org/web/20180806145630/https://www.uu.nl/en/research/research-data-management).

Using the script `cdx_record_fetcher.py` and a list of organisations called `organisations.txt`, it is possible to fetch all CDX Records for each organisation. The output is a `csv`-file per organisation.

### Stage 2: Fetching html pages (page_fetcher)
The next step is to combine the timestamp and url_key to a working url, and fetch the corresponding HTML file. This can be done using the script `page_fetcher.py`, which takes the following arguments:
| Argument      | Description                                     |
|---------------|-------------------------------------------------|
| `data`        | Path to csv data formatted as (timestamp, url). |
| `log`         | Path to log file.                               |
| `bucket_name` | Amazon S3 Bucket name to store HTML files in.   |

If there are many files to be fetched, multiple servers and Ansible should be used. This is described in section Ansible.

### Stage 3: Fetching links from html pages (link_lyxer)
The third step is to convert html files to a list of hyperlinks. This is done using the command line based web browser `lynx` in a Python script called `python/link_lyxer.py`. The input is a directory in the following structure:
```
root
|
organisation domains
|
html_page
```
An example of this could be: `html/uu.nl/20180806145630_uu.nl_en_research_research-data-management`. With this input, the `link_lyxer` will obtain all links and write them per organisation to a single file. The output file has the name `[domain]_links`, i.e.: `uu.nl_links`. Output files will contain the source and destination of a link. An example row can be:
```
uu.nl/20180806145630_uu.nl_en_research_research-data-management∞https://web.archive.org/web/20180806145630/https://www.uu.nl/en/research/research-data-management/guides
```
The source and destination are separated by a delimiter (`∞`), which was picked on it's low likelihood of occurring in an url. All slashes in the source have been replaced with `_`, as `/` can be used in a file name.

### Stage 4: Filtering links (ext_link_lister)
The Python regular expressions library is used in `python/ext_link_lister.py` to filter hyperlinks to organizations in the 'target' list from the list with all hyperlinks in from the previous step. 

## Ansible Workflow
If a fairly large amount of url's needs to be obtained, multiple servers should be used. These servers can be populated using Ansible.

### Stage 1: Obtain the data to fetch
Using the Project Workflow it should be possible to start with a list of organisation domains and end up with a lot of csv's containing CDX Records. These csv files can be combined in the following manner:
```
cd [the correct directory!]
for file in *.csv
do
  # Remove header line
  sed -i '1d' $file
done

# Combine all csv files
cat *.csv > data.csv
```

### Stage 2: Split the data in multiple files
If Stage 1 is completed succesfully, a combined `data.csv` file is obtained which contains all CDX records. Each server will take a slice of this file, and fetch the corresponding records. Splitting this file can be done using `splitter.sh`. It expects the `data.csv` to be in the working directory. It's input argument is the amount of files to create.

Example:
- We have 64 servers, and a file called all_data.csv
- We rename the file to data.csv and open a terminal in that directory
- We run `./splitter.sh 64`

The output of this stage is a folder named `splitting` containing `data0.csv` to `dataX.csv`. All of these files combined would make the original `data.csv`

### Stage 3: Setup AWS
We are using AWS as cloud provider in this project. You will need the following services: S3 & EC2. What is required:
- A created or reused IAM user.
- A bucket with an accessible bucket policy to said IAM user.
- Credentials for said IAM user (resulting in an AWS_Key and AWS_Secret).
- All EC2 instances must be SSH accessible, thus the inbound firewall should allow port 22. This can be accomplished using a custom Security Group.
- The required amount of EC2 instances.
- All EC2 instances should be accessible via *one* ssh key.

### Stage 4: Deploy using Ansible
Ansible is an automation tool that is used to deploy the `page_fetcher` with dependencies in a consistent manner to multiple servers.

The following must be set up in the `hosts` file:
- The hosts files contains an updated list of IP addresses. Using `ansible/get_ip_addresses.sh`, you can obtain this list.
- Variable `ansible_ssh_private_key_file` refers to the correct ssh keyfile in order to access all EC2 instances
- Variable `bucket_name` refers to the correct S3 bucket
- Variable `aws_access_key` refers to AWS Access Key to access the S3 bucket (combo with `aws_secret_key`)
- Variable `aws_secret_key` refers to AWS Secret Key to access the S3 bucket (combo with `aws_access_key`)

After configuring `hosts`, it is possible to run the Ansible playbook using:
```
./run_playbook.sh
```

All variables can be encrypted. In this repo, the AWS credentials have been encrypted and require a vault secret to decrypt. If you run `run_playbook.sh`, a `VAULT_SECRET` is asked by default. If no variables are encrypted, you should remove `--ask-vault-pass` from the bash script.

### Stage 6: Monitoring
There are several ways of monitoring the progress.

#### Checking /tmp/status
```
# Get IP Addresss
aws2 ec2 describe-instances --query 'Reservations[*].Instances[*].[PublicIpAddress]' --filters Name=instance-state-name,Values=running --output text | sort > instances.txt

# Get /tmp/status versus len(data.csv)
cat instances.txt | while read line; do ssh ubuntu@$line 'cat /tmp/status;echo ";";cat /home/aztec/`(ls /home/aztec | grep data)` | wc -l' < /dev/null; echo ";$line"; done
```
Example output is shown below. It means that 1538/3035 records have been fetched.
```
1538;           <-- /tmp/status
3035            <-- length of data.csv
;xx.xxx.xx.xxx  <-- ip
```

#### Checking journalctl
```
ssh -i [path_to_ssh_key] ubuntu@[ip_of_ec2_instance]
journalctl -efu globalgoals.service
```
This will output all logs from the service (the python file wrapped in systemd service).

#### Checking systemd status
```
ssh -i [path_to_ssh_key] ubuntu@[ip_of_ec2_instance]
sudo systemctl status globalgoals.service
```
This will output the systemd status. If the script is running, its status should be on `active (running)`. The script could still be hanging but not crashing, so do check the logs.

#### Checking S3 before and after
```
aws2 s3 ls s3://975435234474-global-goals --recursive | wc -l
```
This will output all files in the S3 bucket. By running this command before deployment and after, it is possible to see the amount of records that have been fetched.

### Stage 5: Fetch logs and terminate servers
Before terminating servers, you should fetch all logs. Logs may explain any errors or mishaps that have occurred while the scripts were running. Save the logs per session per ip.

```
# Create folder
mkdir sess1_64servers
cd sess1_64servers

# Get IP Addresss
aws2 ec2 describe-instances --query 'Reservations[*].Instances[*].[PublicIpAddress]' --filters Name=instance-state-name,Values=running --output text | sort > instances.txt

# Get logs from journalctl
get_journalctl_logs.sh instances.txt
```
This will copy all logs from journalctl to your working directory. Now you can terminate the relevant servers in AWS.

### Stage 6: Parse logs to obtain status
There are two types of logs to parse: journalctl logs and S3 ls logs. The first are the output of the services that run the python scripts, the latter are the result of an list files command of the S3 bucket.

#### Parsing server logs
If Stage 5 was run successfully, you have a folder with logs with filenames such as log123.456.789.txt. The first step is to combine all those log files.
```
cat log*.txt > ../all_logs.txt
```
This will output a file called `all_logs.txt` in the parent directory. The next step is to run `log_parser` over these log files.
```
./log_parser.sh all_logs.txt
```
This will output `all_logs.txt_notfound.csv` and `all_logs.txt_success.csv`. The first file contains all CDX Records that resulted in a 404 error, the latter contains all CDX Records that have been uploaded to S3. Both files are formatted as `timestamp∞url_key`. The columns have been delimited with a `∞` as urls may contain many typical delimiter characters but an infinity sign is very unlikely.

**To get rid of the infinity delimiter:**
1) (Optional) Split the file in multiple csv files when it is too large
   ```
   split -d -n 2 [path_to_csv_file] --additional-suffix=.csv
   ```
1) Open each csv file with excel software (i.e. LibreOffice or Excel)
1) (Optional) If the csv file has been splitted, the last line of the first file may be incomplete and should be combined with the first line of the second file.
1) Save each csv file in another extension (i.e. ods or xlsx)
1) Save each file as csv. This prompt the delimiter choice rather than defaulting to what was already used.
1) (Optional) Combine the split files
   ```
   cat x*.csv > [path_to_output_csv_file]
   ```

#### Parsing AWS S3 ls
To get all the contents of the S3 bucket without actually fetching the files, run `aws2 s3 ls`. Then use `sed` to convert the format to timestamp `timestamp∞url_key`. These steps are shown in the code below:
```
aws2 s3 ls s3://975435234474-global-goals --recursive > downloaded.txt
sed -E 's/.*\/([0-9]{14})_(.*)/\1∞\2/g' downloaded.txt > B.csv
```
This outputs a csv file that is not yet compatible for matching with other csv files. All urls have their slashes(`/`) replaced with underscores(`_`). The original url_keys don't have this. Therefore we have to run a Python file called `reduceAWS.py`. It expects two files: A.csv (all data) and B.csv (S3 ls data).
```
python3 reduceAWS.py
```
This outputs three files:
- matches = A union B
- Aonly   = A - B
- Bonly   = B - A

#### Subtracting fetched and not found from all data
To keep an overview of all subtractions, we can recommend to have aliases for certain types of data, as shown in the table below. If multiple sessions exists, a filename could be C2.csv for the second sessions that produced a C.csv file.
| Filename | Description                                       |
|----------|---------------------------------------------------|
| A        | All data                                          |
| B        | All data in S3 Bucket                             |
| C        | All data from logs that should have been uploaded |
| D        | All data from logs that resulted in a 404         |

To subtract data, `comm` can be used. The files should be sorted beforehand using `sort A.csv > A_sorted.csv`.
```
comm -23 A.csv C.csv > A-C.csv
comm -13 A.csv C.csv > C-A.csv
comm -12 A.csv C.csv > AC.csv
```
These commands above have been incoroporated in the script `calc_unions.sh`. When `./calc_unions.sh A.csv C.csv` is executed, the file counts of each subtractions or union is reported. If the output doesn't make sense, it could be that the format is not the same. `comm` matches per character, so even line-endings could mess the results up. This can be investigated by outputting the head and tail from both files:
```
head A.csv
head C.csv
tail A.csv
tail C.csv
```
If you suspect a line-ending error, run `dos2unix` for both files. Please be aware that csv's have to escape the delimiter if it occurs in the data (i.e.: `x, "y,z"`).

### Stage 7: Redo
When computing A -B -C -D using `comm`, it could be that not all data has been fetched. Start from Stage2 using the subtracted data. Be sure to separate the session's logs and data for proper bookkeeping. For example, split both C.csv files by using C1.csv and C2.csv as filenames.


<!-- CONTACT -->
## Contact

Contact Name - research.engineering@uu.nl

Project Link: [https://github.com/UtrechtUniversity/global-goals](https://github.com/UtrechtUniversity/global-goals)
