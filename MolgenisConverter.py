import argparse, logging, sys, xnat, zipfile

from MolgenisConfigStorage import MolgenisConfigStorage


class MolgenisConverter():
    def __init__(self, args):
        # Get config
        self.config = MolgenisConfigStorage(args)
        # Make connection with XNAT server
        project, connection = self.connect()
        # Get data
        data, headers = self.obtain_data(project, self.config)
        print("Data obtained from XNAT.\n")

        # Write metadata based on headers
        self.write_meta_data(headers, self.config.project_name, self.config.study_id)
        print("Meta data written to files:attributes.csv and packages.csv.\n".format(self.config.project_name,
                                                                                     self.config.study_id))
        # Write data to file
        self.write_data(open("{}_{}.csv".format(self.config.project_name, self.config.study_id), "w"), data, self.meta_data)
        print("Data written to file:{}_{}.csv.\n".format(self.config.project_name, self.config.study_id))

        # Create importable emx
        self.zip_emx()

        connection.disconnect()

        print("Exit.")

    def connect(self):
        """FUNCTION: connect
        PURPOSE: Making connection to the xnat server using xnatpy
        OUT: project and connection"""
        print('Establishing connection\n')
        config = self.config
        try:
            connection = xnat.connect(config.connection_name, user=config.user, password=config.pssw)
            project = connection.projects[config.project_name]
            logging.info("Connection established.")
            return project, connection

        except KeyError:
            print("Project not found in XNAT.\nExit")
            logging.critical("Project not found in XNAT.")
            if __name__ == "__main__":
                sys.exit()
            else:
                return None, None

        except Exception as e:
            print(str(e) + "\nExit")
            if __name__ == "__main__":
                logging.critical(e.message)
                sys.exit()
            else:
                return e, None

    def obtain_data(self, project, config):
        """FUNCTION: obtain_data
        IN: project; the project retrieved from the xnat server using the connect function
            config; the configuration parameters provided in the conf file, parsed using MolgenigConfigStorage
        PURPOSE: obtain the data from the project
        OUT: data_list, a list of rows containing data
             data_header_list, a list of all headers"""
        print('Obtaining data from XNAT\n')
        concept_key_list = []
        data_header_list = []
        data_list = []
        for subject in project.subjects.values():
            data_row_dict = {}
            subject_obj = project.subjects[subject.label]
            for experiment in subject_obj.experiments.values():
                if "qib" in experiment.label.lower() and experiment.project == config.project_name:
                    projectdata_header_list, data_row_dict = self.retrieve_data(subject_obj, experiment, data_row_dict,
                                                                                subject, data_header_list)
            if len(data_row_dict) > 0:
                data_list.append(data_row_dict)

        if data_list == [{}] or data_list == []:
            logging.warning("No QIB datatypes found.")
            print("No QIB datatypes found.\nExit")
            if __name__ == "__main__":
                sys.exit()
            else:
                return data_list
        return data_list, data_header_list

    def retrieve_data(self, subject_obj, experiment, data_row_dict, subject, data_header_list):
        """FUNCTION: retrieve_data
        IN: subject_obj; the object with subject information
            experiment; the experiment object of the subject
            data_row_dict; a dictionary that will contain all data of a row
            subject; the data of the current subject
            data_header; the label of the header we want to put in the row
            data_header_list; list with all header labels
        PURPOSE: retrieve data of a row
        OUT: data_header_list; list with labels of all headers
             data_row_dict; dictionary containing as key the column label and as value the value of that column for one
                            row"""
        session = subject_obj.experiments[experiment.label]
        begin_concept_key = self.write_project_metadata(session)

        data_row_dict['subject'] = subject.label
        if 'subject' not in data_header_list:
            data_header_list.append('subject')

        label_list = experiment.label.split('_')
        metadata = self.get_session_data(subject_obj, label_list)

        for biomarker_category in session.biomarker_categories:
            results = session.biomarker_categories[biomarker_category]

            for biomarker in results.biomarkers:
                concept_value = results.biomarkers[biomarker].value
                concept_key = str(begin_concept_key) + '\\' + str(metadata["scanner"]) + '\\' + str(
                    biomarker_category) + "\\" + metadata["laterality"] \
                              + "\\" + metadata["timepoint"] + "\\" + str(biomarker)
                data_row_dict[concept_key] = concept_value

                if concept_key not in data_header_list:
                    data_header_list.append(concept_key)

        return data_header_list, data_row_dict

    def write_project_metadata(self, session):
        analysis_tool = getattr(session, "analysis_tool")
        analysis_tool_version = getattr(session, "analysis_tool_version")
        if analysis_tool and analysis_tool_version:
            concept_key = str(analysis_tool + " " + analysis_tool_version)
        elif analysis_tool:
            concept_key = (analysis_tool)
        else:
            concept_key = "Generic Tool"
        return concept_key

    def get_session_data(self, subject_obj, label_list):
        """FUNCTION: get_sesssion_data
        IN: subject_obj; the object with subject information
            label_list; a list of all information about the column
        PURPOSE: get the metadata of the data on the server
        OUT: metadata of the data on the xnat server"""
        metadata = {}
        # If the session cannot be found it uses a parsed version of the label to retrieve the needed information.
        try:
            _session = subject_obj.experiments["_".join(label_list[1:])]
            metadata["laterality"] = _session._fields['laterality']
            metadata["timepoint"] = _session._fields['timepoint']
            metadata["scanner"] = _session._fields['scanner']
            metadata["model"] = _session.model
            metadata["manufacturer"] = _session.manufacturer

        except KeyError:
            metadata["laterality"] = label_list[3]
            metadata["timepoint"] = label_list[4]
            metadata["scanner"] = label_list[2]

        return metadata

    def write_data(self, data_file, data_list, data_headers):
        """FUNCTION: write_data
        IN: data_file; the opened file that will contain the data, the filename should be structured like
                        package_entityTypeName.csv as we are used in molgenis
            data_list; a list with dictionaries in this structure: [{column_label1: value1, column_label2: value2},
                        {column_label1: value1, column_label2: value2}]
            data_headers; a dictionary containing the data headers as key and their id's in the molgenis metadata as
                            value
        PURPOSE: write the data to the file in the right format"""
        print('Write data to file\n')
        # Data headers is a dictionary, so we only need its keys, which are the labels of the column when loaded in
        # molgenis. We want to make a row from it in csv format, so comma separated, ending with a blank line. We
        # don't want the labels in the row, but the id's so we take the value of each key in the data_header dictionary
        data_file.write(",".join(['"' + data_headers[header] + '"' for header in data_headers.keys()]) + '\n')
        column_list = []
        rows = []
        subject_written = False
        for line in data_list:
            row = []
            i = 0
            while i < len(data_headers):
                row.append(',')
                i += 1
            for header in data_headers:
                if header in line.keys():
                    info_piece = line[header]
                    index = list(data_headers.keys()).index(header)
                    row[index] = '"' + info_piece + '",'
                    if header == "subject" and subject_written == False:
                        subject_written = True
                        column_list.append(header)
                    elif header not in column_list:
                        column_list.append(header)
            row[-1] = row[-1].replace(',', '\n')
            data_file.write(''.join(row))
            rows.append(row)
        data_file.close()

    def write_meta_data(self, headers, package, entity_name):
        """FUNCTION: write_meta_data
        IN: headers; a dictionary with all headers and the column they should be in (headers could contain all kinds of
            characters, so we use them as labels for all columns instead of id's)
            package; the name of the package, we use project name for it
            entity_name; the name of the table in molgenis, we use study id for it
        PURPOSE: write the attributes, entities and packages file with the metadata for molgenis"""
        print('Write meta data to files\n')
        attribute_file = open("attributes.csv", "w")
        attribute_file.write('"entity","name","label","idAttribute"\n')
        package_file = open("packages.csv", "w")
        entity_file = open("entities.csv", "w")
        self.meta_data = {}
        for i, header in enumerate(headers):
            isId = "FALSE"
            if header == "subject":
                isId = "TRUE"
                attribute_file.write('"{}_{}","{}","{}","{}"\n'.format(package, entity_name, header,header, isId))
                self.meta_data[header] = header
            else:
                attribute_file.write('"{}_{}",column{},"{}","{}"\n'.format(package, entity_name, i,header, isId))
                self.meta_data[header] = "column"+str(i)
        package_file.write('"name"\n"{}"'.format(package))
        entity_file.write('"name","package"\n"{}","{}"'.format(entity_name, package))
        attribute_file.close()
        entity_file.close()
        package_file.close()

    def zip_emx(self):
        """FUNCTION: zip_emx
        PURPOSE: zipping the data and metadata that should be uploaded to molgenis so it can be uploaded"""
        print('Creating zip file from data and meta data: molgenis_import.zip\n')
        emx = zipfile.ZipFile("molgenis_import.zip", "w", zipfile.ZIP_DEFLATED)
        emx.write("{}_{}.csv".format(self.config.project_name, self.config.study_id))
        emx.write("attributes.csv")
        emx.write("packages.csv")
        emx.write("entities.csv")
        emx.close()
        print("Emx created: molgenis-import.zip\nDone")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--connection", help="Location of the configuration file for establishing XNAT connection.")
    args = parser.parse_args()
    MolgenisConverter(args)
