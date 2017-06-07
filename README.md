MolgenisXnatConverter
=====================
**Proof of concept**, only tested for one dataset<br/>
Based on: https://github.com/thehyve/xnat-QIB-TranSMART-import/tree/develop

### Before setup
- Install xnatpy using the xsdparse branch:
```
git clone https://<yourusername>@bitbucket.org/bigr_erasmusmc/xnatpy
git pull feature/xsdparse
python setup.py install
```
### Setup
`python3 MolgenisConverter.py --connection yourconnnectionfile.conf`

### Configutation file example

```[Connection]
url = url of xnat data
user = username
password = password
project = projectname

[Study]
STUDY_ID = studyname
```

### Future work
- Test for other data
- Besides the option to write to file (zip), the option to upload to a specified server using the molgenis API