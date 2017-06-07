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
        print('Obtaining data from XNAT\n')
        concept_key_list = []
        data_header_list = []
        data_list = []
        for subject in project.subjects.values():
            data_row_dict = {}
            subject_obj = project.subjects[subject.label]
            for experiment in subject_obj.experiments.values():
                if "qib" in experiment.label.lower() and experiment.project == config.project_name:
                    projectdata_header_list, data_row_dict, concept_key_list = self.retrieve_QIB(subject_obj,
                                                                                                 experiment,
                                                                                                 data_row_dict, subject,
                                                                                                 data_header_list,
                                                                                                 concept_key_list)
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

    def retrieve_QIB(self, subject_obj, experiment, data_row_dict, subject, data_header_list, concept_key_list):
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

        return data_header_list, data_row_dict, concept_key_list

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
        print('Write data to file\n')
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
                        data_label = header.split("\\")[-1]
                        column_list.append(header)
            row[-1] = row[-1].replace(',', '\n')
            data_file.write(''.join(row))
            rows.append(row)
        data_file.close()

    def write_meta_data(self, headers, package, entity_name):
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
