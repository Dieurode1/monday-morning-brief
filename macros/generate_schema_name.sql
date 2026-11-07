{# Uses each folder's schema name exactly as written, like STAGING or MARTS.
   Without this, dbt would add the default schema as a prefix and create names like STAGING_STAGING. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim | upper }}
    {%- endif -%}
{%- endmacro %}
