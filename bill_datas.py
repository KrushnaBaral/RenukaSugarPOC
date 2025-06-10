def invoice_data(results, bill_data): #bill data for invoices
    for idx, invoice in enumerate(bill_data.documents):
        invoice_data = {}
        vendor_name = invoice.fields.get("VendorName")
        if vendor_name:
            invoice_data["Vendor Name"] = vendor_name.value

        vendor_address = invoice.fields.get("VendorAddress")
        if vendor_address:
            invoice_data["Vendor Address"] = vendor_address.value

        vendor_address_recipient = invoice.fields.get("VendorAddressRecipient")
        if vendor_address_recipient:
            invoice_data["Vendor Address Recipient"] = vendor_address_recipient.content

        customer_name = invoice.fields.get("CustomerName")
        if customer_name:
            invoice_data["Customer Name"] = customer_name.value

        customer_id = invoice.fields.get("CustomerId")
        if customer_id:
            invoice_data["Customer Id"] = customer_id.value

        customer_address = invoice.fields.get("CustomerAddress")
        if customer_address:
            invoice_data["Customer Address"] = customer_address.value

        customer_address_recipient = invoice.fields.get("CustomerAddressRecipient")
        if customer_address_recipient:
            invoice_data["Customer Address Recipient"] = customer_address_recipient.value

        invoice_id = invoice.fields.get("InvoiceId")
        if invoice_id:
            invoice_data["Invoice Id"] = invoice_id.value

        invoice_date = invoice.fields.get("InvoiceDate")
        if invoice_date:
            invoice_data["Invoice Date"] = invoice_date.value

        invoice_total = invoice.fields.get("InvoiceTotal")
        if invoice_total:
            invoice_data["Invoice Total"] = invoice_total.value

        billing_address = invoice.fields.get("BillingAddress")
        if billing_address:
            invoice_data["Billing Address"] = billing_address.value

        billing_address_rec = invoice.fields.get("BillingAddressRecipient")
        if billing_address_rec:
            invoice_data["Billing Address Recipient"] = billing_address_rec.value

    results.append(invoice_data)
    return results
def reciept_data(results, bill_data):
    for idx, receipt in enumerate(bill_data.documents):
        receipt_data = {}

        receipt_type = receipt.doc_type
        if receipt_type:
            receipt_data["Receipt Type"] = receipt_type

        merchant_name = receipt.fields.get("MerchantName")
        if merchant_name:
            receipt_data["Merchant Name"] = merchant_name.value

        transaction_date = receipt.fields.get("TransactionDate")
        if transaction_date:
            receipt_data["Transaction Date"] = transaction_date.value

        subtotal = receipt.fields.get("Subtotal")
        if subtotal:
            receipt_data["Subtotal"] = subtotal.value

        tax = receipt.fields.get("TotalTax")
        if tax:
            receipt_data["Tax"] = tax.value

        tip = receipt.fields.get("Tip")
        if tip:
            receipt_data["Tip"] = tip.value

        total = receipt.fields.get("Total")
        if total:
            receipt_data["Total"] = total.value

    results.append(receipt_data)
    return results
def awb_data(results, bill_data):
    for idx, doc in enumerate(bill_data.documents):
        doc_data = {}

        shipping_address = doc.fields.get('shipping_address')
        if shipping_address.value is not None:
            doc_data["Shipping Address"] = shipping_address.value

        consignee_name = doc.fields.get('consignee_name')
        if consignee_name.value is not None:
            doc_data["Consignee Name"] = consignee_name.value

        shipper_name = doc.fields.get('shipper_name')
        if shipper_name.value is not None:
            doc_data["Shipper Name"] = shipper_name.value

        consignee_address = doc.fields.get('consignee_address')
        if consignee_address.value is not None:
            doc_data["Consignee Address"] = consignee_address.value

        airway_bill_number = doc.fields.get('airway_bill_number')
        if airway_bill_number.value is not None:
            doc_data["Airway Bill Number"] = airway_bill_number.value

        issuer = doc.fields.get('Issuer')
        if issuer.value is not None:
            doc_data["Issuer"] = issuer.value

        total_weight = doc.fields.get('total_weight')
        if total_weight.value is not None:
            doc_data["Total Weight"] = total_weight.value

        execution_date = doc.fields.get('execution_date')
        if execution_date.value is not None:
            doc_data["Execution Date"] = execution_date.value

        total_bill = doc.fields.get('total_bill')
        if total_bill.value is not None:
            doc_data["Total Bill"] = total_bill.value

        currency = doc.fields.get('currency')
        if currency.value is not None:
            doc_data["Currency"] = currency.value

        departure_airport = doc.fields.get('departure_airport')
        if departure_airport.value is not None:
            doc_data["Departure Airport"] = departure_airport.value

        destination_airport = doc.fields.get('destination_airport')
        if destination_airport.value is not None:
            doc_data["Destination Airport"] = destination_airport.value

        shipper_account_number = doc.fields.get('Shipper_account_number')
        if shipper_account_number.value is not None:
            doc_data["Shipper Account Number"] = shipper_account_number.value
        results.append(doc_data)
    return results

# def renuka_data(results, bill_data):
#     for idx, doc in enumerate(bill_data.documents):
#         doc_data = {}

#         invoice_no = doc.fields.get("Invoice Number")
#         if invoice_no and invoice_no.value is not None:
#             doc_data["Invoice Number"] = invoice_no.value

#         gstin = doc.fields.get("GSTIN")
#         if gstin and gstin.value is not None:
#             doc_data["GSTIN"] = gstin.value

#         vendor_name = doc.fields.get("Vendor Name")
#         if vendor_name and vendor_name.value is not None:
#             doc_data["Vendor Name"] = vendor_name.value

#         description = doc.fields.get("Description")
#         if description and description.value is not None:
#             doc_data["Description"] = description.value

#         date = doc.fields.get("Invoice Date")
#         if date and date.value is not None:
#             doc_data["Invoice Date"] = date.value

#         total_amount = doc.fields.get("Total Amount (In Ruppees)")
#         if total_amount and total_amount.value is not None:
#             doc_data["Total Amount (In Ruppees)"] = total_amount.value

#         list_items = doc.fields.get("List Items")
#         if list_items and list_items.value is not None:
#             # Print table header
#             print("| # | Description of Goods | Qty | Weight | Rate | Amount |")
#             print("|---|---|---|---|---|---|")

#             for i, item in enumerate(list_items.value, 1):
#                 desc = item.value.get("Description of Goods")
#                 qty = item.value.get("Qty.")
#                 weight = item.value.get("Weight")
#                 rate = item.value.get("Rate")
#                 amount = item.value.get("Amount")

#                 # Get the values or empty string if None
#                 desc_val = desc.value if desc and desc.value is not None else ""
#                 qty_val = qty.value if qty and qty.value is not None else ""
#                 weight_val = weight.value if weight and weight.value is not None else ""
#                 rate_val = rate.value if rate and rate.value is not None else ""
#                 amount_val = amount.value if amount and amount.value is not None else ""

#                 # Print each row
#                 print(f"| {i} | {desc_val} | {qty_val} | {weight_val} | {rate_val} | {amount_val} |")



#         results.append(doc_data)
#         # print(results)

#     return results
def renuka_data(results, bill_data):
    for idx, doc in enumerate(bill_data.documents):
        doc_data = {}

        # Extract basic fields
        invoice_no = doc.fields.get("Invoice Number")
        if invoice_no and invoice_no.value is not None:
            doc_data["Invoice Number"] = invoice_no.value

        gstin = doc.fields.get("GSTIN")
        if gstin and gstin.value is not None:
            doc_data["GSTIN"] = gstin.value

        vendor_name = doc.fields.get("Vendor Name")
        if vendor_name and vendor_name.value is not None:
            doc_data["Vendor Name"] = vendor_name.value

        description = doc.fields.get("Description")
        if description and description.value is not None:
            doc_data["Description"] = description.value

        date = doc.fields.get("Invoice Date")
        if date and date.value is not None:
            doc_data["Invoice Date"] = date.value

        total_amount = doc.fields.get("Total Amount (In Ruppees)")
        if total_amount and total_amount.value is not None:
            doc_data["Total Amount (In Ruppees)"] = total_amount.value

        # Process List Items as a table
        list_items = doc.fields.get("List Items")
        if list_items and list_items.value is not None:
            table_data = {
                "table_number": 1,
                "cells": []
            }

            # Add header row
            headers = ["SL No", "Description of Goods", "Qty", "Weight", "Rate", "Amount"]
            for col_idx, header in enumerate(headers):
                table_data["cells"].append({
                    "row_index": 0,
                    "column_index": col_idx,
                    "content": header
                })

            # Add data rows
            for row_idx, item in enumerate(list_items.value, 1):
                desc = item.value.get("Description of Goods")
                qty = item.value.get("Qty.")
                weight = item.value.get("Weight")
                rate = item.value.get("Rate")
                amount = item.value.get("Amount")

                # Get values or empty string if None
                values = [
                    str(row_idx),
                    desc.value if desc and desc.value is not None else "",
                    qty.value if qty and qty.value is not None else "",
                    weight.value if weight and weight.value is not None else "",
                    rate.value if rate and rate.value is not None else "",
                    amount.value if amount and amount.value is not None else ""
                ]

                for col_idx, value in enumerate(values):
                    table_data["cells"].append({
                        "row_index": row_idx,
                        "column_index": col_idx,
                        "content": value
                    })

            doc_data["tables"] = [table_data]

        results.append(doc_data)

    return results
def packing_data(results, bill_data):
    for idx, doc in enumerate(bill_data.documents):
        doc_data = {}

        vendor_address = doc.fields.get('VendorAddress')
        if vendor_address.value is not None:
            doc_data["Vendor Address"] = vendor_address.value

        billing_address = doc.fields.get('BillingAddress')
        if billing_address.value is not None:
            doc_data["Billing Address"] = billing_address.value

        shipping_address = doc.fields.get('ShippingAddress')
        if shipping_address.value is not None:
            doc_data["Shipping Address"] = shipping_address.value

        vendor_name = doc.fields.get('VendorName')
        if vendor_name.value is not None:
            doc_data["Vendor Name"] = vendor_name.value

        invoice_date = doc.fields.get('InvoiceDate')
        if invoice_date.value is not None:
            doc_data["Invoice Date"] = invoice_date.value

        customer_name = doc.fields.get('CustomerName')
        if customer_name.value is not None:
            doc_data["Customer Name"] = customer_name.value

        shipping_date = doc.fields.get('shipping_date')
        if shipping_date.value is not None:
            doc_data["Shipping Date"] = shipping_date.value

        customer_email = doc.fields.get('customer_email')
        if customer_email.value is not None:
            doc_data["Customer Email"] = customer_email.value

        order_no = doc.fields.get('OrderNo')
        if order_no.value is not None:
            doc_data["Order Number"] = order_no.value

    results.append(doc_data)
    return results