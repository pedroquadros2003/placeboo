import calendar

MONTH_NAME_TO_NUM = {
    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6,
    'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12,
    # Keeping English names for future-proofing or other potential uses
    'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6, 
    'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12,
}

def get_days_for_month(year_str, month_name_str):
    """
    Returns the number of days in a given month and year.
    Handles leap years for February.
    Returns 0 if year or month is not a valid number/name.
    """
    try:
        year = int(year_str)
        # Get month number from name using the dictionary
        month = MONTH_NAME_TO_NUM.get(month_name_str)
        if not month:
            return 0
        return calendar.monthrange(year, month)[1]
    except (ValueError, TypeError):
        return 0
