# Fly and Create its4land  tool

### Create Docker image
```
docker build . -t flyandcreate
```

### Usage
```
docker run --env I4L_PROJECTUID=8d377f30-d244-41b9-9f97-39a711b4679a --env I4L_PROCESSUID=2f8dc5ee-3a82-4893-9e71-7479582bfa50 --env I4L_PUBLICAPIURL=https://platform.its4land.com/api flyandcreate --texturing-nadir-weight urban --spatial-source-id 487c67f5-7820-4d1b-bc0b-274c59157053 --dsm --pc-las
```
