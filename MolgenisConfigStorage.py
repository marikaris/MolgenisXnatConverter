import sys, logging

if sys.version_info.major == 3:
    import configparser as ConfigParser
elif sys.version_info.major == 2:
    import ConfigParser

class MolgenisConfigStorage():
    """This class retrieves the content of the provided config file and stores it"""
    def __init__(self, args):
        config_bool = False
        if args.__contains__("connection") and args.__dict__["connection"]:
            config_connection = self.check_config_existence(args.connection, "connection")
            self.set_connection_conf(config_connection)
            config_bool = True
        if not config_bool:
            self.error = "No configuration files given.\nExit"

    def set_connection_conf(self, config_connection):
        """
        Function: Sets the variables from the connection configurations
        Parameters:
             -config_connection     String      Path to configuration file
        """
        self.connection_name = config_connection.get('Connection', 'url')
        self.user = config_connection.get('Connection', 'user')
        self.pssw = config_connection.get('Connection', 'password')
        self.project_name = config_connection.get('Connection', 'project')
        self.study_id = config_connection.get('Study', "STUDY_ID")

    def check_config_existence(self, file_, type):

        """
        Function: Checks if the configuration file exists and reads its content.
        Parameters:
            -file_      String      Path to configuration file.
            -type       String      Which type of configuration file.
        Returns:
            -config     Config      Parsed configuration file object.
        """
        try:
            file_test = open(file_, 'r')
            config = ConfigParser.SafeConfigParser()
            config.read(file_)
            file_test.close()
            return config

        except IOError:
            print("%s config file not found") % type
            logging.critical(type + " config file not found")
            sys.exit()
