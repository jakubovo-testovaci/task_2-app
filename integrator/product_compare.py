from .product_validate import Product
from .product_type import ProductTransformed, ProductType, ProductTransformedWithoutHash, ProductTransformedForPatch
from .models import Item
from typing import List, Dict
from pydantic import ValidationError

""" necha erp data zvalidovat a upravit a porovna s DB - hleda chybejici a zmenene
pripravi data pro odeslani na API (props missing a differing) a po zavolani save_missing_to_db() a save_differing_to_db()
dane zmeny ulozi do DB """
class ProductCompare:
    def __init__(self, data: List[ProductType]):
        self.__db_items_for_insert: List[Item] = []
        self.__db_items_for_update: List[Item] = []
        self.__load(data)
        self.__compare()

    @property
    def missing(self) -> List[ProductTransformedWithoutHash]:
        return self.__missing

    @property
    def differing(self) -> List[ProductTransformedForPatch]:
        return self.__differing
    
    def save_missing_to_db(self):
        Item.objects.bulk_create(self.__db_items_for_insert, batch_size=1000)

    def save_differing_to_db(self):
        db_fields = Item.get_data_fields()
        db_fields.append("hash")
        Item.objects.bulk_update(self.__db_items_for_update, db_fields, batch_size=1000)
    
    def __compare(self):
        product_in_db = Item.objects.filter(source_id__in=self.__products.keys())
        product_in_db_map = {item.source_id: item for item in product_in_db}

        self.__missing: List[ProductTransformedWithoutHash] = []  # produkty, které v DB chybí
        self.__differing: List[ProductTransformedForPatch] = []  # produkty, které se liší (hash mismatch)
        db_fields = Item.get_data_fields()

        for sku, ext_item in self.__products.items():
            db_item = product_in_db_map.get(sku)
            if not db_item:
                # produkt není v DB
                ext_item_wo_hash = ext_item.copy()
                ext_item_wo_hash.pop("hash", None)
                self.__missing.append(self.__replace_source_id_with_id(ext_item_wo_hash))
                self.__db_items_for_insert.append(Item(**ext_item))

            elif db_item.hash != ext_item["hash"]:
                # hash se liší – připrav data pro PATCH
                patch_data = {'id': sku}
                for field in db_fields:
                    if getattr(db_item, field) != ext_item[field]:
                        setattr(db_item, field, ext_item[field])
                        patch_data[field] = ext_item[field]
                db_item.hash = ext_item["hash"]
                self.__differing.append(patch_data)
                self.__db_items_for_update.append(db_item)

    def __load(self, data: List[ProductType]):
        self.__products: Dict[str, ProductTransformed] = {}
        for product_raw in data:
            try:
                product = Product(**product_raw)
                self.__products[product.id] = product.transformed
            except ValidationError as e:
                print('validation error')
                print({'errors': e.errors(), 'data': product_raw})

    def __replace_source_id_with_id(self, input: Dict) -> Dict:
        output = {'id': input['source_id']}
        for key, item in input.items():
            if key != 'source_id':
                output[key] = item
        return output