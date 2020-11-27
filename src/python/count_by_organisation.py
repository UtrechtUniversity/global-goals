import csv
import tldextract


def main():
  parser = argparse.ArgumentParser(description='Count data by organisation.')
  parser.add_argument("--data", "-d", help="Path to csv data formatted as (timestamp, url).", default="./data.csv")
  args = parser.parse_args()
  domains = {}
  with open(args.data, newline='') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    for row in spamreader:
      ext = tldextract.extract(row[1])
      if ext.subdomain:
        domain = ext.subdomain + "." + ext.domain + "." + ext.suffix
      else:
        domain = ext.domain + "." + ext.suffix
      if domain not in domains:
        domains[domain] = 1
      else:
        domains[domain] = domains[domain] + 1
  for key, value in domains.items():
    print(f"{key}, {value}")
  return domains

if __name__ == "__main__":
  main()
