import argparse
import csv

def read_file(file_path, delimiter=","):
    with open(file_path) as csv_file:
        list_ = []
        csv_reader = csv.reader(csv_file, delimiter=delimiter)
        for row in csv_reader:
            list_.append(row)
        return list_

matches = []
Aonly = []
Bonly = []


def compare(listA, listB, indexA=0, indexB=0):
    listA_filled = indexA + 1 == len(listA)
    listB_filled = indexB + 1 == len(listB)

    if listA_filled or listB_filled:
        if listB_filled:
            Aonly.append(indexA)
            indexA += 1
        if listA_filled:
            Bonly.append(indexB)
            indexB += 1
        return indexA, indexB

    rowA = listA[indexA]
    rowB = listB[indexB]
    tsA = int(rowA[0])
    tsB = int(rowB[0])

    # Timestamps match
    if tsA == tsB:
        urlA = rowA[1].replace("/", "_")
        urlB = rowB[1].replace("/", "_")
        # Url key match
        if urlA == urlB:
            matches.append((indexA, indexB))
            indexA += 1
            indexB += 1
        # Url key don't match
        elif urlA > urlB:
            Bonly.append(indexB)
            indexB += 1
        else:
            Aonly.append(indexA)
            indexA += 1

    # Timestamps don't match
    elif tsA > tsB:
        Bonly.append(indexB)
        indexB += 1
    else:
        Aonly.append(indexA)
        indexA += 1

    return indexA, indexB


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch pages from the Internet Archive.')
    parser.add_argument("-csv1", default="A.csv")
    parser.add_argument("-delim1", default=",")
    parser.add_argument("-csv2", default="B.csv")
    parser.add_argument("-delim2", default=",")
    args = parser.parse_args()

    a = read_file(args.csv1, args.delim1)
    b = read_file(args.csv2, args.delim2)
    indexA = 0
    indexB = 0
    while indexA < len(a) or indexB < len(b):
        indexA, indexB = compare(a, b, indexA, indexB)
    print(len(matches))


    with open('matches.csv', 'w') as csvfile:
        for match in matches:
            spamwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(a[match[0]])

    with open('only_first.csv', 'w') as csvfile:
        for a_record in Aonly:
            spamwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(a[a_record])
    print(len(Aonly))

    with open('only_second.csv', 'w') as csvfile:
        for b_record in Bonly:
            spamwriter = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            spamwriter.writerow(b[b_record])
    print(len(Bonly))
