import json

from json_value_history.controller import SaveController
from json_value_history.models import DiffTypeEnum
from json_value_history.util import pprint


def run():
    saver = SaveController()
    saver.init({
        "name": "양지훈",
        "mail": "zhuny936772@gmail.com",
        "github": "https://github.com/zhuny",
        "experience": [{
            'company_name': "엑스 주식회사",
            'start_date': "2020-02-10",
            'end_date': None
        }]
    })
    pprint(saver.get_latest())  # init해둔 값을 확인할 수 있다.

    info = saver.get_latest_with_structure()  # front에서 통신하기 위한 내용들 포함
    saver.append(info['experience'].attr, {
        'company_name': "무브 주식회사",
        'start_date': "2017-07-10",
        'end_date': "2019-12-31"
    })  # 새로운 값 추가
    saver.change(
        info['experience'][0]['company_name'].attr,
        "액스 주식회사"
    )  # 오타 수정 ㅋㅋㅋ
    pprint(saver.get_latest())  # submit 하기 전이라 예전 값 보여야 됨
    saver.submit()
    pprint(saver.get_latest())  # submit 이후에 적용된 값이 보여야 됨

    # 이번 수정에서 변경된 값을 확인한다.
    action_command_name = {
        DiffTypeEnum.CREATE: "추가",
        DiffTypeEnum.EDIT: "수정",
        DiffTypeEnum.DELETE: "삭제",
    }
    for history in saver.get_latest_history():
        action_commend = action_command_name[history.diff_type]
        print(
            f"{history.next_attr}의 값이 "
            f"{history.prev_value!r}에서 {history.next_value!r}로 "
            f"{action_commend}되었습니다."
        )


if __name__ == '__main__':
    run()
