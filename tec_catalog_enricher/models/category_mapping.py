from odoo import fields, models, api
from google import genai
from google.genai import types
import logging

_logger = logging.getLogger(__name__)
SUITE_LOG_PREFIX = "[Tec Suite] Brain Hub: "

class CategoryMapping(models.Model):
    _name = 'tec.catalog.category.mapping'
    _description = 'Supplier to MELI Category Mapping'
    _order = 'supplier_category_name'

    supplier_category_name = fields.Char(string='Supplier Category', required=True, index=True)
    public_category_id = fields.Many2one('product.public.category', string='MELI/Public Category')
    confidence = fields.Float(string='AI Confidence', readonly=True)
    
    _sql_constraints = [
        ('uniq_supplier_cat', 'unique(supplier_category_name)', 'Supplier category must be unique!')
    ]

    @api.model
    def match_category(self, supplier_cat_name):
        """ Find match or create mapping request """
        mapping = self.search([('supplier_category_name', '=', supplier_cat_name)], limit=1)
        if mapping and mapping.public_category_id:
            return mapping.public_category_id
        
        # If no mapping, we could trigger AI? 
        # Or just return None and let a batch process handle it?
        # For now, let's just return None.
        return None

    @api.model
    def action_generate_ai_mappings(self):
        """ Bulk Process unmapped categories using Gemini """
        # 1. Get Setup
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('tec_catalog_enricher.gemini_api_key')
        if not api_key:
            _logger.warning(f"{SUITE_LOG_PREFIX}No Gemini API Key found in settings.")
            return

        # 2. Get unmapped mappings (or new ones from products?)
        # Strategy: We need a list of ALL supplier categories currently in use.
        # Let's verify against products.
        products = self.env['product.template'].search([('categ_id', '!=', False)])
        # This uses internal category. 
        # But we want "Rubro" from supplier.
        # Air Backend creates categories like "Notebooks".
        # So we can search product.category where parent is "Dropship/Air"!
        
        air_root = self.env['product.category'].search([('name', '=', 'Dropship/Air')], limit=1)
        if not air_root:
            return
            
        supplier_cats = self.env['product.category'].search([('parent_id', 'child_of', air_root.id)])
        
        # 3. Get MELI Categories for Context (Roots or all?)
        # Passing ALL is too big. 
        # We'll ask Gemini to "Hallucinate" the best path or provide a candidate?
        # Better: We assume we have fetched MELI categories into product.public.category.
        # We can pass a list of Root MELI Categories to guide it?
        
        target_cats = self.env['product.public.category'].search([('parent_id', '=', False)])
        target_names = [c.name for c in target_cats]
        
        client = genai.Client(api_key=api_key)
        
        for cat in supplier_cats:
            # Check if mapped
            existing = self.search([('supplier_category_name', '=', cat.name)], limit=1)
            if existing and existing.public_category_id:
                continue
            
            if not existing:
                existing = self.create({'supplier_category_name': cat.name})
            
            # AI Call
            prompt = f"""
            Act as an E-commerce Expert. Map the supplier category '{cat.name}' to the best matching MercadoLibre Argentina Category.
            Available Top-Level Categories: {', '.join(target_names)}.
            
            Return ONLY the exact Name of the target category. If it's a subcategory, format as 'Parent > Child'.
            """
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash', 
                    contents=prompt
                )
                predicted_name = response.text.strip()
                _logger.info(f"{SUITE_LOG_PREFIX}AI Prediction for {cat.name} -> {predicted_name}")
                
                # Try to find this category in DB
                # Split by > and find leaf?
                leaf_name = predicted_name.split('>')[-1].strip()
                public_cat = self.env['product.public.category'].search([('name', 'ilike', leaf_name)], limit=1)
                
                if public_cat:
                    existing.public_category_id = public_cat.id
                    existing.confidence = 0.9 # Fake confidence
            except Exception as e:
                _logger.error(f"Gemini Error: {e}")

