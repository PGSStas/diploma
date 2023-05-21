MONTH_TO_NUMBER = {
    'января': 1,
    'февраля': 2,
    'марта': 3,
    'апреля': 4,
    'мая': 5,
    'июня': 6,
    'июля': 7,
    'августа': 8,
    'сентября': 9,
    'октября': 10,
    'ноября': 11,
    'декабря': 12,
}


def transform_date(date: str) -> str:
    """
    Transforms strange IXBT format to ours
    22 апреля 2023 в 15:35 -> 22.04.2023 15:35:00 (Europe/Moscow)
    """
    splited = date.split()
    return "{:02}.{:02}.{} {}:00 (Europe/Moscow)".format(int(splited[0]), int(MONTH_TO_NUMBER[splited[1]]), splited[2], splited[4])
