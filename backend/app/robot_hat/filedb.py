import os
import json
from time import sleep


class fileDB(object):
    """A file based database.

    A file based database, read and write arguements in the specific file.
    """

    def __init__(self, db: str):
        """
        Init the db_file is a file to save the datas.

        :param db: the file to save the datas.
        :type db: str
        :param mode: the mode of the file.
        :type mode: str
        :param owner: the owner of the file.
        :type owner: str
        """

        self.db = db
        # Check if db_file is existed, otherwise create one
        if self.db != None:
            self.file_check_create(db)
        else:
            raise ValueError("db: Missing file path parameter.")

    def file_check_create(
        self,
        file_path: str,
    ):
        """
        Check if file is existed, otherwise create one.

        :param file_path: the file to check
        :type file_path: str
        :param mode: the mode of the file.
        :type mode: str
        :param owner: the owner of the file.
        :type owner: str
        """
        dir = file_path.rsplit("/", 1)[0]
        try:
            if os.path.exists(file_path):
                if not os.path.isfile(file_path):
                    print("Could not create file, there is a folder with the same name")
                    return
            else:
                if os.path.exists(dir):
                    if not os.path.isdir(dir):
                        print(
                            "Could not create directory, there is a file with the same name"
                        )
                        return
                else:
                    os.makedirs(name=dir, mode=0o754, exist_ok=True)
                    sleep(0.001)

                with open(file_path, "w") as f:
                    f.write("# robot-hat config and calibration value of robots\n\n")

        except Exception as e:
            raise (e)

    def get(self, name, default_value=None):
        """
        Get value with data's name

        :param name: the name of the arguement
        :type name: str
        :param default_value: the default value of the arguement
        :type default_value: str
        :return: the value of the arguement
        :rtype: str
        """
        try:
            value = None  # Initialize value to handle potential unbound variable
            with open(self.db, "r") as conf:
                lines = conf.readlines()

            file_len = len(lines) - 1
            flag = False

            for i in range(file_len):
                if lines[i][0] != "#":
                    if lines[i].split("=")[0].strip() == name:
                        value = lines[i].split("=")[1].replace(" ", "").strip()
                        flag = True
                        break

            return value if flag else default_value

        except FileNotFoundError:
            with open(self.db, "w") as conf:
                conf.write("")
            return default_value
        except Exception:
            return default_value

    def set(self, name, value):
        """
        Set value by with name. Or create one if the arguement does not exist

        :param name: the name of the arguement
        :type name: str
        :param value: the value of the arguement
        :type value: str
        """
        # Read the file
        conf = open(self.db, "r")
        lines = conf.readlines()
        conf.close()
        file_len = len(lines) - 1
        flag = False
        # Find the arguement and set the value
        for i in range(file_len):
            if lines[i][0] != "#":
                if lines[i].split("=")[0].strip() == name:
                    lines[i] = "%s = %s\n" % (name, value)
                    flag = True
        # If arguement does not exist, create one
        if not flag:
            lines.append("%s = %s\n\n" % (name, value))

        # Save the file
        conf = open(self.db, "w")
        conf.writelines(lines)
        conf.close()

    def get_all_as_json(self):
        """
        Get all key-value pairs as a JSON string.

        :return: the key-value pairs in JSON format
        :rtype: str
        """
        try:
            data = {}
            with open(self.db, "r") as conf:
                lines = conf.readlines()

            for line in lines:
                if line.strip() and line[0] != "#":
                    key, value = line.split("=")
                    data[key.strip()] = value.replace(" ", "").strip()

            return json.dumps(data, indent=4)
        except Exception as e:
            raise Exception(f"Failed to parse database file: {e}")
