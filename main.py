import billing
import refund


def welcome():
    print("=" * 40)
    print(" AI Customer Support Automation ")
    print("=" * 40)


def main():
    welcome()

    billing.billing_menu()

    refund.refund_menu()


if __name__ == "__main__":
    main()