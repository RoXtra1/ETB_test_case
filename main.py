from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from decimal import Decimal
import xml.etree.ElementTree as ET
from xml.dom import minidom
from models import *

DB_NAME = "energotransbank_test"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = 5432

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

def menu():
    print("\nМеню:")
    print("1 - Просмотр списка клиентов и их счетов")
    print("2 - Проводка между счетами")
    print("3 - Экспорт списка клиентов со счетами в XML")
    print("4 - Импорт списка клиентов со счетами из XML")
    print("5 - Просмотр истории операций")
    print("0 - Выход")

def create_tables():
    try:
        Base.metadata.create_all(engine)
        print("В базе данных 'energotransbank_test' есть необходимые таблицы")

    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")

def fill_tables(session):
    names = ["Иванов Иван Иванович", "Петров Петр Петрович", "Скорняков Артём Сергеевич"]
    numbers = ["0001", "0002", "0003"]
    balances = [10000, 20000, 30000]

    for i in range(len(names)):
        new_client = Client(name=names[i], id=i)
        session.add(new_client)
        session.flush()

    for i in range(len(numbers)):
        id = i+1 if i<2 else i

        new_account = Account(
            client_id=id,
            account_number=numbers[i],
            balance=balances[i]
        )
        session.add(new_account)
        session.flush()
        print(f"Счет {new_account.account_number} принадлежит пользователю {new_account.client.name}")

def show_clients_list(session):
    clients = session.query(Client).order_by(Client.id).all()

    if not clients:
        print("В базе нет клиентов.")
        return

    print("\nСписок клиентов и их счетов:")
    for client in clients:
        print(f"Клиент {client.id}: {client.name}")

        if not client.accounts:
            print("----Нет счетов")
            continue

        for account in client.accounts:
            print(f"----Номер счета: {account.account_number}, Баланс: {account.balance} руб.")

def provodka(session):
    accounts = session.query(Account).all()

    if len(accounts) < 2:
        print("Ошибка: Для осуществления перевода требуется минимум 2 счета")
        return

    print("\nДоступные счета:")
    for acc in accounts:
        print(f"- {acc.account_number} ({acc.client.name}): {acc.balance} руб.")

    from_account = input("\nСчет списания (номер): ").strip()
    to_account = input("Счет зачисления (номер): ").strip()

    try:
        amount = Decimal(input("Сумма перевода: "))
        if amount <= 0:
            print("Сумма должна быть положительной")
            return
    except ValueError:
        print("Некорректная сумма")
        return

    try:
        acc_from = session.query(Account).filter_by(account_number=from_account).first()
        acc_to = session.query(Account).filter_by(account_number=to_account).first()

        if not acc_from or not acc_to:
            print("Один из счетов не найден")
            return

        if acc_from == acc_to:
            print("Переводить на тот же счет не имеет смысла")
            return

        if acc_from.balance < amount:
            print(f"Недостаточно средств. Доступно: {acc_from.balance} руб.")
            return

        acc_from.balance -= amount
        acc_to.balance += amount

        transaction = Transactions(
            from_account=acc_from.account_number,
            to_account=acc_to.account_number,
            amount=amount)
        session.add(transaction)

        print(f"\nПеревод выполнен успешно!")
        print(f"Со счета {acc_from.account_number} списано: {amount} руб.")
        print(f"На счет {acc_to.account_number} зачислено: {amount} руб.")
        print(f"Остатки по счетам:")
        print(f"- {acc_from.account_number}: {acc_from.balance} руб.")
        print(f"- {acc_to.account_number}: {acc_to.balance} руб.")

    except Exception as e:
        print(f"Ошибка при выполнении проводки: {e}")
        raise

def export_to_xml(session, filename="clients_export.xml"):
    try:
        clients = session.query(Client).options(joinedload(Client.accounts)).all()
        root = ET.Element("BankData")

        for client in clients:
            client_elem = ET.SubElement(root, "Client")
            ET.SubElement(client_elem, "ID").text = str(client.id)
            ET.SubElement(client_elem, "Name").text = client.name

            accounts_elem = ET.SubElement(client_elem, "Accounts")
            for account in client.accounts:
                account_elem = ET.SubElement(accounts_elem, "Account")
                ET.SubElement(account_elem, "Number").text = account.account_number
                ET.SubElement(account_elem, "Balance").text = str(account.balance)

        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)

        print(f"Данные успешно экспортированы в {filename}")
        return True

    except Exception as e:
        print(f"Ошибка экспорта: {e}")
        return False

def import_from_xml(session, filename="import.xml"):
    try:
        tree = ET.parse(filename)
        root = tree.getroot()

        for client_elem in root.findall('Client'):
            client = Client(
                id=int(client_elem.find('ID').text),
                name=client_elem.find('Name').text
            )
            session.add(client)  # добавление данных о клиентах в бд
            session.flush()  # временное применение внесенных изменений для использования их в последующих изменениях

            accounts_elem = client_elem.find('Accounts')
            for account_elem in accounts_elem.findall('Account'):
                account = Account(
                    account_number=account_elem.find('Number').text,
                    balance=Decimal(account_elem.find('Balance').text),
                    client_id=client.id
                )
                session.add(account)  # добавление данных об аккаунтах клиента в бд

        print(f"Данные успешно импортированы из {filename}")
        return True

    except Exception as e:
        print(f"Ошибка при импорте: {e}")
        raise

def transaction_history(session):
    print("\nИстория операций:")
    print("1 - По конкретному счету")
    print("2 - Все операции")
    choice = input("Выберите вариант: ")

    try:
        if choice == "1":
            account_num = input("Введите номер счета: ").strip()
            transactions = session.query(Transactions).filter((Transactions.from_account == account_num) |
                           (Transactions.to_account == account_num)).order_by(Transactions.date.desc()).all()
        elif choice == "2":
            transactions = session.query(Transactions).order_by(Transactions.date.desc()).all()
        else:
            print("Некорректный выбор")
            return

        if not transactions:
            print("Операции не найдены")
            return

        print("\nДата\t\t\t\tОт кого\t\tКому\t\tСумма")
        print("-" * 55)
        for t in transactions:
            print(
                f"{t.date.strftime('%Y-%m-%d %H:%M')}\t{t.from_account}\t\t{t.to_account}\t\t{t.amount}")

    except Exception as e:
        print(f"Ошибка при получении истории: {e}")


if __name__ == "__main__":
    create_tables()  # создание пустых табличек

    Session = sessionmaker(bind=engine)  # создание экземпляра сессии

    # if session.query(Client).first() is None:  # таблицы заполняются если отсутствуют клиенты
    #     try:
    #         # fill_tables(session)  функция для заполнения начальными данными не из xml
    #         session.commit()
    #     except Exception as e:
    #         session.rollback()
    #         print(f"Ошибка при заполнении таблиц: {e}")
    # else:
    #     print("В таблице содержатся записи")

    while True:
        menu()
        event = input("\nВыберите действие: ")

        if event == "1":
            with Session(bind=engine.execution_options(readonly=True)) as read_session:  # открытие транзакции исключительно для чтения данных
                show_clients_list(read_session)
        elif event == "2":
            with Session() as session:  # такая же автоматическая точка входа в транзакцию
                with session.begin():  # точка входа в транзакцию для реализации проводки. автоматически закрывается и автоматически делает откат в случае сбоя
                    provodka(session)
        elif event == "3":
            with Session(bind=engine.execution_options(readonly=True)) as read_session:
                export_to_xml(read_session)
        elif event == "4":
            name = input("Ведите название файла (по дефолту - import.xml)").strip()
            with Session() as session:
                with session.begin():
                    if name:
                        import_from_xml(session, name)
                    else:
                        import_from_xml(session)
        elif event == "5":
            with Session(bind=engine.execution_options(readonly=True)) as read_session:
                transaction_history(read_session)
        elif event == "0":
            print("\nВыход из программы...")
            break
        else:
            print("Некорректный ввод, попробуйте снова")
