from fpdf import FPDF

def generate_invoice_pdf(invoice, format_currency):
    """Generates a clean PDF invoice using pure Python (fpdf2)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Colors
    pdf.set_text_color(30, 41, 59) # Dark Navy
    
    # Header
    pdf.set_font("Helvetica", "B", 26)
    pdf.cell(0, 10, "INVOICE", new_x="LMARGIN", new_y="NEXT", align="R")
    
    pdf.set_font("Helvetica", "B", 16)
    business_name = invoice["profile"].get("business_name") or invoice["profile"].get("full_name") or "Freelance Billing"
    pdf.set_xy(10, 10)
    pdf.cell(0, 8, business_name, new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139) # Muted
    pdf.cell(0, 5, invoice["profile"].get("full_name", ""), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"{invoice['profile'].get('email', '')} | {invoice['profile'].get('phone', '')}", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_y(40)
    
    # Meta Information
    pdf.set_text_color(30, 41, 59)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(110, 6, "Billed To:")
    
    pdf.cell(40, 6, "Invoice Number:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(40, 6, invoice["invoice_number"], new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(110, 6, invoice["client_name"])
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 6, "Date:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(40, 6, str(invoice.get("invoice_date", "")), new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(110, 6, invoice.get("client_company", ""))
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 6, "Due Date:")
    pdf.set_font("Helvetica", "B", 10)
    if invoice["status"] == "Overdue":
        pdf.set_text_color(220, 38, 38)
    pdf.cell(40, 6, str(invoice.get("due_date", "")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(30, 41, 59)
    
    pdf.set_y(80)
    
    # Table Header
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(241, 245, 249) # Light gray
    pdf.cell(15, 8, "#", border=1, fill=True)
    pdf.cell(85, 8, "Description", border=1, fill=True)
    pdf.cell(20, 8, "Hrs", border=1, fill=True, align="R")
    pdf.cell(30, 8, "Rate", border=1, fill=True, align="R")
    pdf.cell(30, 8, "Amount", border=1, fill=True, align="R", new_x="LMARGIN", new_y="NEXT")
    
    # Table Rows
    pdf.set_font("Helvetica", "", 10)
    for i, item in enumerate(invoice["line_items"], 1):
        desc = item["description"]
        if len(desc) > 42:
            desc = desc[:39] + "..."
            
        pdf.cell(15, 8, str(i), border=1)
        pdf.cell(85, 8, desc, border=1)
        pdf.cell(20, 8, str(item["hours"]), border=1, align="R")
        pdf.cell(30, 8, format_currency(item["hourly_rate"], invoice["currency"]).replace("₹", "INR "), border=1, align="R")
        pdf.cell(30, 8, format_currency(item["amount"], invoice["currency"]).replace("₹", "INR "), border=1, align="R", new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(5)
    
    # Totals
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 6, "")
    pdf.cell(30, 6, "Subtotal:", align="R")
    pdf.cell(30, 6, format_currency(invoice["subtotal"], invoice["currency"]).replace("₹", "INR "), align="R", new_x="LMARGIN", new_y="NEXT")
    
    if float(invoice.get("discount_amount", 0)) > 0:
        pdf.cell(120, 6, "")
        pdf.set_text_color(4, 120, 87)
        pdf.cell(30, 6, f"Discount ({invoice['discount_percent']}%):", align="R")
        pdf.cell(30, 6, f"-{format_currency(invoice['discount_amount'], invoice['currency']).replace('₹', 'INR ')}", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(30, 41, 59)
        
    if float(invoice.get("tax_amount", 0)) > 0:
        pdf.cell(120, 6, "")
        pdf.cell(30, 6, f"Tax ({invoice['tax_percent']}%):", align="R")
        pdf.cell(30, 6, f"+{format_currency(invoice['tax_amount'], invoice['currency']).replace('₹', 'INR ')}", align="R", new_x="LMARGIN", new_y="NEXT")
        
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(120, 8, "")
    pdf.cell(30, 8, "Total Due:", align="R")
    pdf.cell(30, 8, format_currency(invoice["total"], invoice["currency"]).replace("₹", "INR "), align="R", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    if invoice.get("payment_terms"):
        pdf.multi_cell(0, 5, f"Terms: {invoice['payment_terms']}")
    if invoice.get("notes"):
        pdf.multi_cell(0, 5, f"Notes: {invoice['notes']}")
        
    return bytes(pdf.output())
