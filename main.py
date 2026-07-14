import billing
import refund


def show_main_menu():
    print("\n====================================")
    print("   AI Customer Support Automation")
    print("====================================")
    print("1. Billing Support")
    print("2. Refund Support")
    print("3. Exit")


def main():
    while True:
        show_main_menu()

        choice = input("\nEnter your choice: ")

        if choice == "1":
            billing.billing_menu()

        elif choice == "2":
            refund.refund_menu()

        elif choice == "3":
            print("\nThank you for using Customer Support AI.")
            break;

        else:
            print("\nInvalid choice. Please try again.")
            


if __name__ == "__main__":
    main()