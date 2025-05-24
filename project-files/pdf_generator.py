from fpdf import FPDF
from datetime import datetime

class DentalReportPDF(FPDF):
    def __init__(self, patient_name=None):
        super().__init__()
        
        self.add_page()
        self.set_auto_page_break(True, margin=15)
        self.set_margins(10, 10, 10)
        
        
        self.patient_name = patient_name if patient_name else "Patient"
        
        
        self.primary_dark = (26, 31, 44)
        self.secondary = (100, 255, 218)
        self.accent = (136, 207, 255)
        self.text_white = (255, 255, 255)
        self.text_light = (226, 232, 240)
        self.bg_card = (30, 35, 45)
        self.table_header = (46, 51, 64)

    def create_header(self):
        """Create the report header with title and date"""
        
        self.set_fill_color(*self.primary_dark)
        self.rect(0, 0, 210, 22, 'F')
        
        
        self.set_y(5)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.text_light)
        self.cell(0, 5, 'َANODYNE Analysis Service', 0, 1, 'L')
        
        
        self.set_y(10)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(*self.secondary)
        self.cell(0, 10, 'Dental Analysis Report', 0, 1, 'C')
        
        
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*self.text_light)
        self.set_y(17)
        self.cell(100, 5, f'Patient: {self.patient_name}', 0, 0, 'L')
        self.cell(0, 5, f'Date: {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'R')
        
        self.ln(10)

    def create_footer(self):
        """Add footer with page number and service info"""
        self.set_y(-15)
        self.set_fill_color(*self.primary_dark)
        self.rect(0, self.h-15, 210, 15, 'F')
        
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*self.text_light)
        self.cell(100, 10, 'DentalAI Analysis Service', 0, 0, 'L')
        self.cell(0, 10, f'Page {self.page_no()} / {{nb}}', 0, 0, 'R')

    def chapter_title(self, title, num=None):
        """Add a main chapter title with numbering"""
        self.set_font('Helvetica', 'B', 14)
        self.set_fill_color(*self.primary_dark)
        self.set_text_color(*self.secondary)
        
        
        self.rect(10, self.get_y(), 190, 10, 'F')
        
        
        if num:
            self.cell(0, 10, f' {num}. {title}', 0, 1, 'L')
        else:
            self.cell(0, 10, f' {title}', 0, 1, 'L')
        
        self.ln(5)

    def section_title(self, title):
        """Add a section title with background"""
        self.set_font('Helvetica', 'B', 12)
        self.set_fill_color(*self.bg_card)
        self.set_text_color(*self.accent)
        self.cell(0, 8, f' {title}', 0, 1, 'L', 1)
        self.ln(4)

    def section_text(self, text, indent=0):
        """Add regular section text with optional indent"""
        self.set_font('Helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        self.set_x(10 + indent)
        self.multi_cell(190 - indent, 6, text)
        self.ln(4)

    def add_findings_summary_table(self, class_counts, total_detections):
        """Create a table summarizing findings by category and count"""
        if not class_counts:
            self.section_text("No issues detected in the analysis.")
            return
        
        
        col_width = [130, 30, 30]
        row_height = 8
        
        
        self.set_fill_color(*self.table_header)
        self.set_text_color(*self.text_white)
        self.set_font('Helvetica', 'B', 10)
        
        
        self.cell(col_width[0], row_height, ' Finding Category', 1, 0, 'L', 1)
        self.cell(col_width[1], row_height, 'Count', 1, 0, 'C', 1)
        self.cell(col_width[2], row_height, 'Percentage', 1, 1, 'C', 1)
        
        
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(240, 240, 240)
        
        fill = False
        for class_name, count in class_counts.items():
            percentage = (count / total_detections) * 100 if total_detections > 0 else 0
            self.cell(col_width[0], row_height, f' {class_name}', 1, 0, 'L', fill)
            self.cell(col_width[1], row_height, str(count), 1, 0, 'C', fill)
            self.cell(col_width[2], row_height, f'{percentage:.1f}%', 1, 1, 'C', fill)
            fill = not fill
        
        self.ln(5)

    def add_processing_details(self, model_name, confidence, exec_time):
        """Add a box with processing details"""
        self.set_font('Helvetica', 'B', 10)
        self.set_fill_color(*self.bg_card)
        self.set_text_color(*self.text_white)
        self.cell(0, 8, ' Processing Details', 1, 1, 'L', 1)
        
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(245, 245, 245)
        
        
        confidence_pct = min(confidence * 100 if confidence < 1 else confidence, 100)
        
        details = [
            ['Model Used:', model_name],
            ['Confidence Score:', f'{confidence_pct:.1f}%'],
            ['Processing Time:', f'{exec_time:.2f} seconds']
        ]
        
        fill = True
        for label, value in details:
            self.cell(60, 7, f' {label}', 1, 0, 'L', fill)
            self.cell(130, 7, f' {value}', 1, 1, 'L', fill)
            fill = not fill
        
        self.ln(5)

    def add_recommendation_box(self, title, count, recommendations):
        """Add a recommendation box with title and bullet points"""
        
        self.set_fill_color(*self.bg_card)
        self.set_text_color(*self.accent)
        self.set_font('Helvetica', 'B', 11)
        
        
        self.cell(0, 8, f' {title} (Detected: {count})', 1, 1, 'L', 1)
        
        
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)
        self.set_fill_color(248, 248, 248)
        
        if recommendations:
            for i, item in enumerate(recommendations):
                self.set_x(15)
                self.cell(5, 6, '-', 0, 0)
                self.multi_cell(0, 6, item, 'LR' if i == 0 else 'LR', 'L', 1)
            
            
            self.set_x(10)
            self.cell(0, 0, '', 'T', 1)
        else:
            self.set_x(15)
            self.cell(5, 6, '-', 'L', 0)
            self.multi_cell(0, 6, "No specific recommendations available for this finding.", 'R', 'L', 1)
            self.set_x(10)
            self.cell(0, 0, '', 'T', 1)
        
        self.ln(5)

    def create_table_of_contents(self):
        """Create a simple table of contents"""
        self.section_title("Contents")
        
        sections = [
            "Analysis Summary",
            "Detailed Findings & Recommendations",
            "Next Steps",
            "Important Information"
        ]
        
        for i, section in enumerate(sections):
            self.set_font('Helvetica', '', 10)
            self.cell(10, 6, f"{i+1}.", 0, 0)
            self.set_font('Helvetica', 'U', 10)
            self.set_text_color(*self.primary_dark)
            self.cell(0, 6, section, 0, 1)
        
        self.ln(5)

def generate_prediction_pdf(prediction_result: dict, recommendations_map: dict, patient_name=None) -> bytes:
    """Generate a PDF report based on prediction results and recommendations"""
    
    try:
        
        pdf = DentalReportPDF(patient_name)
        pdf.alias_nb_pages()
        pdf.create_header()
        
        
        pdf.create_table_of_contents()
        
        
        pdf.chapter_title("Analysis Summary", 1)
        
        
        model_name = prediction_result.get('model_name', 'Advanced Dental AI')
        total_detections = prediction_result.get('total_detections', 0)
        confidence = prediction_result.get('confidence_score', 0.0)
        exec_time = prediction_result.get('execution_time', 0.0)
        class_counts = prediction_result.get('class_counts', {})
        
        
        if total_detections > 0:
            intro_text = (
                f"Thank you for using our dental analysis service. We've analyzed your dental images "
                f"and identified {total_detections} area(s) that might need attention. Below is a "
                f"summary of our findings:"
            )
        else:
            intro_text = (
                f"Thank you for using our dental analysis service. We've analyzed your dental images "
                f"and didn't detect any areas requiring immediate attention. Here's a summary of our analysis:"
            )
        
        pdf.section_text(intro_text)
        
        
        pdf.add_findings_summary_table(class_counts, total_detections)
        
        
        pdf.add_processing_details(model_name, confidence, exec_time)
        
        
        pdf.chapter_title("Detailed Findings & Recommendations", 2)
        
        if not class_counts:
            no_detection_key = "NO_RELEVANT_FINDINGS"
            no_detection_recommendations = recommendations_map.get(no_detection_key, [
                "No specific dental conditions requiring intervention were detected.",
                "Continue with regular dental check-ups and maintain good oral hygiene practices.",
                "Consider scheduling your next routine dental examination within 6 months."
            ])
            pdf.add_recommendation_box("No Areas of Concern", 0, no_detection_recommendations)
        else:
            
            sorted_classes = sorted(class_counts.keys())
            
            
            for class_name in sorted_classes:
                count = class_counts[class_name]
                
                
                recommendations_list = recommendations_map.get(class_name, [])
                if not recommendations_list:
                    
                    recommendations_list = recommendations_map.get(class_name.upper(), [])
                
                
                if not recommendations_list:
                    recommendations_list = [
                        f"Please consult with your dentist about the detected {class_name} findings.",
                        "Maintain regular dental hygiene including brushing and flossing."
                    ]
                
                
                pdf.add_recommendation_box(class_name, count, recommendations_list)
        
        
        pdf.chapter_title("Next Steps", 3)
        next_steps = [
            "Share this report with your dentist at your next appointment.",
            "Follow any specific care instructions from your dental professional.",
            "Consider scheduling a follow-up scan in 6-12 months.",
            "Maintain good oral hygiene habits: brush twice daily and floss regularly."
        ]
        
        for step in next_steps:
            pdf.set_x(15)
            pdf.cell(5, 6, "-", 0, 0)
            pdf.multi_cell(0, 6, step)
        
        pdf.ln(5)
        
        
        pdf.chapter_title("Important Information", 4)
        disclaimer_text = (
            "This automated analysis is for informational purposes only and does not replace "
            "a professional dental examination. The accuracy of the findings depends on image "
            "quality and other factors. Always consult with your dentist for proper diagnosis "
            "and treatment recommendations."
        )
        pdf.section_text(disclaimer_text)
        
        
        pdf.create_footer()
        
        
        return pdf.output(dest='S').encode('latin1')
    
    except Exception as e:
        
        error_pdf = FPDF()
        error_pdf.add_page()
        error_pdf.set_font('Helvetica', 'B', 16)
        error_pdf.cell(0, 10, 'We encountered an issue with your report', 0, 1, 'C')
        error_pdf.set_font('Helvetica', '', 12)
        error_pdf.cell(0, 10, f"Our team has been notified and will fix this soon. Error details: {str(e)}", 0, 1, 'C')
        return error_pdf.output(dest='S').encode('latin1')



if __name__ == '__main__':
    from recommendations import ICDAS_RECOMMENDATIONS
    
    print("Loading recommendations from recommendations.py...")
    for key in ICDAS_RECOMMENDATIONS:
        print(f"Found recommendation category: {key} with {len(ICDAS_RECOMMENDATIONS[key])} items")
    
    
    sample_prediction_result_with_findings = {
        'processed_image': b'',
        'class_counts': {
            'SOUND_OR_SEALED': 3,
            'INITIAL_CARIES_ENAMEL': 2,
            'MODERATE_CARIES_DENTINE': 1
        },
        'total_detections': 6,
        'model_name': 'DentalAI-v4.2',
        'confidence_score': 0.947,
        'execution_time': 0.95
    }
    
    
    
    sample_prediction_high_confidence = {
        'processed_image': b'',
        'class_counts': {
            'INITIAL_CARIES_ENAMEL': 3,
            'EXTENSIVE_CARIES_DENTINE': 1
        },
        'total_detections': 4,
        'model_name': 'DentalAI-v4.2',
        'confidence_score': 9.47,
        'execution_time': 0.75
    }
    
    
    sample_prediction_no_findings = {
        'processed_image': b'',
        'class_counts': {},
        'total_detections': 0,
        'model_name': 'DentalAI-v4.2',
        'confidence_score': 0.0,
        'execution_time': 0.75
    }

    
    try:
        print("\nGenerating PDF with findings...")
        
        pdf_bytes_with_findings = generate_prediction_pdf(
            sample_prediction_result_with_findings,
            ICDAS_RECOMMENDATIONS,
            "John Doe"
        )
        with open("dental_report_with_findings.pdf", "wb") as f:
            f.write(pdf_bytes_with_findings)
        print("Successfully generated: dental_report_with_findings.pdf")
        
        print("\nGenerating PDF with high confidence (test capping)...")
        pdf_bytes_high_confidence = generate_prediction_pdf(
            sample_prediction_high_confidence,
            ICDAS_RECOMMENDATIONS,
            "Jane Smith"
        )
        with open("dental_report_high_confidence.pdf", "wb") as f:
            f.write(pdf_bytes_high_confidence)
        print("Successfully generated: dental_report_high_confidence.pdf")
        
        print("\nGenerating PDF without findings...")
        
        pdf_bytes_no_findings = generate_prediction_pdf(
            sample_prediction_no_findings,
            ICDAS_RECOMMENDATIONS,
            "No Findings Test"
        )
        with open("dental_report_no_findings.pdf", "wb") as f:
            f.write(pdf_bytes_no_findings)
        print("Successfully generated: dental_report_no_findings.pdf")
        
        print("\nSummary of recommendation keys used:")
        for key in sample_prediction_result_with_findings['class_counts']:
            if key in ICDAS_RECOMMENDATIONS:
                print(f"✓ Key '{key}' found in recommendations")
            else:
                print(f"✗ Key '{key}' NOT found in recommendations")
    
    except Exception as e:
        print(f"Error testing PDF generation: {str(e)}")