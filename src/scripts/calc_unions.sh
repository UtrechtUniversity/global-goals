# Calculate differences and unions between lists

echo "First only"
comm -23 $1 $2 | wc -l
echo
echo "Second only"
comm -13 $1 $2 | wc -l
echo
echo "Union first,second"
comm -12 $1 $2 | wc -l


