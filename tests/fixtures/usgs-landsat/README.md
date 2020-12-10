
Test files created with:

```bash
mkdir -p collection02/level-2/standard/oli-tirs/2020/001/062/LC08_L2SP_001062_20201031_20201106_02_T2/
cd collection02/level-2/standard/oli-tirs/2020/001/062/LC08_L2SP_001062_20201031_20201106_02_T2/
aws s3 cp --recursive s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/001/062/LC08_L2SP_001062_20201031_20201106_02_T2/ . --request-payer

find . -name '*.TIF' | while read line; do
    b=$(echo $line | sed 's/.TIF/_s.TIF/g');
    echo $b;
    gdal_translate -outsize 5% 5% $line $b;
    rio cogeo create $b $line --blocksize 128;
    rm $line;
    mv $b $line;
done
```
