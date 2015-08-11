import sys
from sqlalchemy import Column, ForeignKey, Integer, String, BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class Category(Base):
    '''Category mapping class for category table'''
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)

    # Serialize all the required attributes
    @property
    def serialize(self):
        return{
            'name': self.name
        }


class CategoryItem(Base):
    '''Category Item mapping class for category item table'''
    __tablename__ = 'category_item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(250), nullable=True)
    image = Column(BLOB, nullable=True)
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)

    # Serialize all the required attributes
    @property
    def serialize(self):
        return{
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'category_name': self.category.name,
        }

# Create sqlite db
engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Delete all CategoryItem rows
session.query(CategoryItem).delete()
session.commit()

# Delete all Category rows
session.query(Category).delete()
session.commit()

category_list = ['Soccer', 'Basketball', 'Baseball', 'Frisbee', 'Snowboarding',
                 'Rock Climbing', 'Foosball', 'Skating', 'Hockey']

# Iterate through category list and add it to Category table
for cat in category_list:
    newCategory = Category(name=cat)
    session.add(newCategory)
session.commit()

# Add category items to category item table.
newItem = CategoryItem(name="Soccer Cleats", description="description",
                       category_id=1)
session.add(newItem)
newItem = CategoryItem(name="Jersey", description="description", category_id=1)
session.add(newItem)
newItem = CategoryItem(name="Soccer Socks", description="description",
                       category_id=1)
session.add(newItem)
newItem = CategoryItem(name="Basketball Hoops", description="description",
                       category_id=2)
session.add(newItem)
newItem = CategoryItem(name="Basketball Shoes", description="description",
                       category_id=2)
session.add(newItem)

newItem = CategoryItem(name="Baseball Bat", description="description",
                       category_id=3)
session.add(newItem)
newItem = CategoryItem(name="Baseball Helmet", description="description",
                       category_id=3)
session.add(newItem)
newItem = CategoryItem(name="Frisbee Disc", description="description",
                       category_id=4)
session.add(newItem)
newItem = CategoryItem(name="Snowboarding Goggles", description="description",
                       category_id=5)
session.add(newItem)
newItem = CategoryItem(name="Snowboarding Jacket", description="description",
                       category_id=5)
session.add(newItem)
newItem = CategoryItem(name="Snowboard", description="description",
                       category_id=5)
session.add(newItem)
newItem = CategoryItem(name="Rope", description="description", category_id=6)
session.add(newItem)
newItem = CategoryItem(name="Helmet", description="description",
                       category_id=6)
session.add(newItem)
newItem = CategoryItem(name="Foosball board", description="description",
                       category_id=7)
session.add(newItem)

newItem = CategoryItem(name="Skating shoes", description="description",
                       category_id=8)
session.add(newItem)
newItem = CategoryItem(name="Hockey bat", description="description",
                       category_id=9)
session.add(newItem)
session.commit()
