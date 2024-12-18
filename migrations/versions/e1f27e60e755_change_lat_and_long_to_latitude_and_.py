"""Change lat and long to latitude and longitude

Revision ID: e1f27e60e755
Revises: 
Create Date: 2024-12-12 01:36:37.975802

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f27e60e755'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Mengubah nama kolom 'lat' menjadi 'latitude' dan 'long' menjadi 'longitude'
    with op.batch_alter_table('location_settings', schema=None) as batch_op:
        batch_op.alter_column('lat', new_column_name='latitude')
        batch_op.alter_column('long', new_column_name='longitude')


def downgrade():
    # Mengembalikan nama kolom 'latitude' menjadi 'lat' dan 'longitude' menjadi 'long'
    with op.batch_alter_table('location_settings', schema=None) as batch_op:
        batch_op.alter_column('latitude', new_column_name='lat')
        batch_op.alter_column('longitude', new_column_name='long')