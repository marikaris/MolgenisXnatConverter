# MolgenisXnatConverter
Based on: https://github.com/thehyve/xnat-QIB-TranSMART-import/tree/develop

Before setup:
- Install xnatpy using the xsdparse branch:
```
git clone https://<yourusername>@bitbucket.org/bigr_erasmusmc/xnatpy
git pull feature/xsdparse
python setup.py install
```
Now the program can be used using: <br/>
`python3 MolgenisConverter.py --connection yourconnnectionfile.conf`

The connection configuration file should look like:

```[Connection]
url = url of xnat data
user = username
password = password
project = projectname

[Study]
STUDY_ID = studyname
```