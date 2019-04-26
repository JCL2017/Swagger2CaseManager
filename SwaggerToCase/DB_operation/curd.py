import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from SwaggerToCase.DB_operation.models import Project, \
    TestCase, Config, StepCase, API, Validate, Extract, \
    Parameters, Variables

engine = create_engine("mysql+pymysql://root:ate.sqa@127.0.0.1:3306/swagger?charset=utf8",
                       encoding='utf-8',
                       # echo=True,
                       max_overflow=5)
Session = sessionmaker(bind=engine)
session = Session()


class CURD(object):
    def __init__(self):
        pass

    # 适合新的测试用例的create（ TODO ：需要，models中新增config的variable表，CURD支持Variable的CURD）
    # 然后在这个基础上修改（如：parameters、variables、name等等）
    # 也适合流程场景测试testcase的create
    # 新增testcase, 把teststep1对应的初始testcase查询出来
    # 然后在这个testcase基础上进行修改
    def add_case(self, old_case_id, case_name):
        old_case_obj = session.query(TestCase).filter(TestCase.id == old_case_id)
        new_case_obj = TestCase(name=case_name, project_id=old_case_obj.project_id)
        session.add(new_case_obj)
        session.commit()

        old_config_obj = session.query(Config).filter(Config.testcase_id == old_case_id).join(TestCase).first()
        name = old_config_obj.name  # ToDo 支持config name 的update（其实这个就是testcasename，测试用例描述）
        body = old_config_obj.body
        config_obj = Config(name=name, body=body, testcase_id=new_case_obj.id)
        session.add(config_obj)
        session.commit()

        old_teststeps_obj = session.query(StepCase).filter(StepCase.testcase_id == old_case_id).join(TestCase).all()
        for old_step_obj in old_teststeps_obj:
            name = old_step_obj.name
            api_name = old_step_obj.api_name
            body = old_step_obj.body
            step_obj = StepCase(name=name, step=1, api_name=api_name, body=body, testcase_id=new_case_obj.id)
            session.add(step_obj)
            session.commit()

    def add_variable(self, config_id, variable):
        # 注意：这里variable是字符串（传进来需要json转换）
        key = variable['key']
        value = variable["value"]
        variable_obj = Variables(key=key,
                                 value=value,
                                 config_id=config_id)
        session.add(variable_obj)
        session.commit()

    def add_parameter(self, config_id, parameter):
        key = parameter['key']
        value = parameter["value"]
        parameter_obj = Parameters(key=key,
                                   value=value,
                                   config_id=config_id)
        session.add(parameter_obj)
        session.commit()

    def add_step(self, case_id, test_step, step_pos):
        name = test_step["name"]
        step = step_pos
        api_name = test_step["api"]
        body = json.dumps({"test": test_step})
        testcase_id = case_id
        step_obj = StepCase(name=name,
                            step=step,
                            api_name=api_name,
                            body=body,
                            testcase_id=testcase_id)
        session.add(step_obj)
        session.commit()

    def add_validate(self, step_id, validate):
        comparator = validate['comparator']
        check = validate["check"]
        expected = validate["expected"]
        validate_obj = Validate(comparator=comparator,
                                check=check,
                                expected=expected,
                                stepcase_id=step_id)
        session.add(validate_obj)
        session.commit()

    def add_extract(self, step_id, extract):
        key = extract['key']
        value = extract["value"]
        extract_obj = Extract(key=key,
                              value=value,
                              stepcase_id=step_id)
        session.add(extract_obj)
        session.commit()

    def delete_project(self, project_id):
        testcases_obj = session.query(TestCase).filter(TestCase.project_id == project_id).join(TestCase).all()
        [self.delete_case(test_case) for test_case in testcases_obj]
        session.query(Project).filter_by(id=project_id).delete()
        session.commit()

    def delete_case(self, case_id):
        # session.query(TestCase).filter_by(id=case_id).delete()  # 只是这样，删不了，因为有config和stepcase通过外键引用
        # 要想删除testcase, 先删除config和teststep
        # 同理，要想删除config，先删除parameters和variables
        # 要想删除teststep，先删除api(这个不合适)、validate和extract
        config_obj = session.query(Config).filter(Config.testcase_id == case_id).join(TestCase).first()
        self.delete_config(config_obj.id)
        teststeps_obj = session.query(StepCase).filter(StepCase.testcase_id == case_id).join(TestCase).all()
        [self.delete_setp(teststep.id) for teststep in teststeps_obj]
        session.query(TestCase).filter_by(id=case_id).delete()
        session.commit()

    def delete_config(self, config_id):
        config_obj = session.query(Config).filter(Config.id == config_id)
        parameters_obj = session.query(Parameters). \
            filter(Parameters.config_id == config_obj.id).join(Config, isouter=True).all()
        [self.delete_parameter(parameter.id) for parameter in parameters_obj]
        variables_obj = session.query(Variables). \
            filter(Variables.config_id == config_obj.id).join(Config, isouter=True).all()
        [self.delete_variable(variable.id) for variable in variables_obj]
        session.query(Config).filter_by(id=config_id).delete()
        session.commit()

    def delete_parameter(self, parameter_id):
        session.query(Parameters).filter_by(id=parameter_id).delete()
        session.commit()

    def delete_variable(self, variable_id):
        session.query(Variables).filter_by(id=variable_id).delete()
        session.commit()

    def delete_setp(self, step_id):
        step_obj = session.query(Config).filter(Config.id == step_id)
        validates_obj = session.query(Validate). \
            filter(Validate.stepcase_id == step_obj.id).join(StepCase, isouter=True).all()
        [self.delete_validate(validate.id) for validate in validates_obj]
        extracts_obj = session.query(Extract). \
            filter(Extract.stepcase_id == step_obj.id).join(StepCase, isouter=True).all()
        [self.delete_variable(extract.id) for extract in extracts_obj]
        session.query(StepCase).filter_by(id=step_id).delete()
        session.commit()

    def delete_validate(self, validate_id):
        session.query(Validate).filter_by(id=validate_id).delete()
        session.commit()

    def delete_extract(self, extract_id):
        session.query(Extract).filter_by(id=extract_id).delete()
        session.commit()

    # update testcase:
    #       update config:
    #              add_parameter、update_parameter、delelte_parameter
    #              add_variable、update_variable、delelte_variable
    #       update teststep:
    #              add_validate、update_validate、delete_validate
    #              add_extract、update_extract、delete_extract
    def update_parameter(self, config_id, parameter):
        key = parameter['key']
        value = parameter["value"]
        parameter_obj = session.query(Parameters).filter(Parameters.id == config_id)
        parameter_obj.key = key
        parameter_obj.value = value
        session.add(parameter_obj)
        session.commit()

    def update_variable(self, config_id, variable):
        key = variable['key']
        value = variable["value"]
        variable_obj = session.query(Variables).filter(variable.id == config_id)
        variable_obj.key = key
        variable_obj.value = value
        session.add(variable_obj)
        session.commit()

    def update_validate(self, validate_id, validate):
        comparator = validate['comparator']
        check = validate["check"]
        expected = validate["expected"]
        validate_obj = session.query(Validate).filter(Validate.id == validate_id)
        validate_obj.comparator = comparator
        validate_obj.check = check
        validate_obj.expected = expected
        session.add(validate_obj)
        session.commit()

    def update_extract(self, step_id, extract):
        key = extract['key']
        value = extract["value"]
        extract_obj = session.query(Extract).filter(Extract.id == step_id)
        extract_obj.key = key
        extract_obj.value = value
        session.add(extract_obj)
        session.commit()

    def retrieve_parameter(self, parameter_id):
        '''
        配合parameter元素的update和delete
        先查出来，获取id，然后进行update或delete
        :param parameter_id:
        :return:
        '''
        parameter = session.query(Parameters).filter_by(id=parameter_id).first()
        element = {
            "id": parameter.id,
            "key": parameter.key,
            "value": parameter.value,
            "config_id": parameter.config_id
        }
        return element

    def retrieve_variable(self, variable_id):
        '''
        配合variable元素的update和delete
        :param variable_id:
        :return:
        '''
        variable = session.query(Variables).filter_by(id=variable_id).first()
        element = {
            "id": variable.id,
            "key": variable.key,
            "value": json.loads(variable.value),
            "config_id": variable.config_id
        }
        return element

    def retrieve_validate(self, validate_id):
        '''
        配合parameter元素的update和delete
        :param validate_id:
        :return:
        '''
        validate = session.query(Validate).filter_by(id=validate_id).first()
        element = {
            "id": validate.id,
            "comparator": validate.comparator,
            "check": validate.check,
            "expected": validate.expected,
            "stepcase_id": validate.stepcase_id
        }
        return element

    def retrieve_extract(self, extract_id):
        '''
        配合parameter元素的update和delete
        :param extract_id:
        :return:
        '''
        extract = session.query(Extract).filter_by(id=extract_id).first()
        element = {
            "id": extract.id,
            "key": extract.key,
            "value": json.loads(extract.value),
            "stepcase_id": extract.stepcase_id
        }
        return element

    # TODO：待拆分
    def retrieve_part_cases(self, case_ids):
        '''
        从数据库中查询并组装好某个project中某些测试用例用于测试执行
        :param pro_name:
        :param case_ids:
        :return:
        '''
        test_cases = session.query(TestCase).filter(TestCase.id.in_(case_ids)).all()
        testcases = []  # 要执行的测试用例
        testapis = []  # 测试用例执行相关的api
        for case_obj in test_cases:
            case_name = case_obj.name
            test_case = []  # testcase, include config and teststeps
            print("case : ", case_obj)

            # ----------------------------测试用例的config数据 ----------------------------
            config_obj = session.query(Config).filter(Config.testcase_id == case_obj.id).join(TestCase).first()
            print("config: ", config_obj)
            case_config = json.loads(config_obj.body)

            # parameters of config
            parameters_obj = session.query(Parameters). \
                filter(Parameters.config_id == config_obj.id).join(Config, isouter=True).all()
            print("parameters: ", parameters_obj)
            parameter_list = []
            for item in parameters_obj:
                element = {item.key: item.value}
                parameter_list.append(element)
            case_config["config"].update({"parameters": parameter_list})

            # variables of config
            variables_obj = session.query(Variables). \
                filter(Variables.config_id == config_obj.id).join(Config, isouter=True).all()
            print("variables: ", variables_obj)
            variable_list = []
            for item in variables_obj:
                element = {item.key: json.loads(item.value)}
                variable_list.append(element)
            case_config["config"].update({"variables": variable_list})

            test_case.append(case_config)

            # ----------------------------测试用例的teststeps数据 ----------------------------
            teststeps_obj = session.query(StepCase).filter(StepCase.testcase_id == case_obj.id).join(TestCase).all()
            print(type(teststeps_obj), teststeps_obj)
            case_steps = []  # teststeps
            teststeps_obj = sorted(teststeps_obj, key=lambda x: x.step)
            for step_obj in teststeps_obj:
                print("step: ", step_obj)

                step = json.loads(step_obj.body)  # teststep的主体信息

                # testcase corresponding api
                step_name = step["test"]["name"]
                names = [test_api["api"]["name"] for test_api in testapis]
                if step_name not in names:
                    api_obj = session.query(API).filter(API.name == step_name).first()
                    api = json.loads(api_obj.body)  # api的主体信息
                    testapis.append(api)

                # validate of teststep
                validates_obj = session.query(Validate).filter(Validate.stepcase_id == step_obj.id).join(StepCase,
                                                                                                         isouter=True).all()
                # if validates_obj is not None:
                print("validates: ", validates_obj)
                validate_list = []
                for item in validates_obj:
                    comparator = item.comparator
                    check = item.check
                    expected = item.expected
                    if expected in ["200", "404", "500", "401"]:
                        expected = int(expected)
                    element = {comparator: [check, expected]}
                    validate_list.append(element)
                step["test"].update({"validate": validate_list})  # teststep中的validate可能会add\update\delete，所以要update

                # validate of teststep
                extracts_obj = session.query(Extract). \
                    filter(Extract.stepcase_id == step_obj.id).join(StepCase, isouter=True).all()
                print("extracts: ", extracts_obj)
                extract_list = []
                for item in extracts_obj:
                    element = {item.key: item.value}
                    extract_list.append(element)
                step["test"].update({"extract": extract_list})  # teststep中的extract可能会add\update\delete，所以要update

                case_steps.append(step)

            test_case = test_case + case_steps
            testcases.append((case_name, test_case))

        return testapis, testcases

    def retrieve_one_caase(self, case_id):
        testapis, testcases = self.retrieve_part_cases([case_id])
        return case_id, testcases[0]

    def retrive_project_cases(self, project_id):
        project_obj = session.query(Project).filter(Project.id == project_id).first()
        testcases_obj = session.query(TestCase).filter(TestCase.project_id == project_obj.id).join(Project).all()
        case_id_names = [(case.id, case.name) for case in testcases_obj]
        return case_id_names