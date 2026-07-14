def billing_menu():
    print("\n========== Billing Support ==========")
    print("1. Check Payment Status")
    print("2. Download Invoice")
    print("3. View Subscription")
    print("4. Back")

    choice = input("\nEnter Billing Option: ")

    if choice == "1":
        print("\nChecking Payment Status...")

    elif choice == "2":
        print("\nPreparing Invoice Download...")

    elif choice == "3":
        print("\nFetching Subscription Details...")

    elif choice == "4":
        print("\nReturning to Main Menu...")

    else:
        print("\nInvalid Billing Option.")