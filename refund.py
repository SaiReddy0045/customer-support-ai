from secrets import choice


def refund_menu():
    print("\n===== Refund Support =====")
    print("1. Check Refund Status")
    print("2. Refund Policy")
    print("3.Request refund")
    print("4.Back")

    choice = input("\nEnter Refund Option: ")

    if(choice=="1"):
        print("\nChecking Refund Status...")
    elif(choice=="2"):
        print("\nFetching Refund Policy...")
    elif(choice=="3"): 
        print("\nProcessing Refund Request...")
    elif(choice=="4"):
        print("\nReturning to Main Menu...")
    else:
        print("\nInvalid Refund Option.")