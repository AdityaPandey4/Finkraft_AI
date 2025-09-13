Basic Queries (Clear and Actionable):

   * Show me the first 5 rows of the dataset.
   * What are the different regions in the dataset?
   * Calculate the total net revenue.
   * Group by region and calculate the average units sold.
   * Sort the data by net revenue in descending order.

  Vague Queries (To Test Suggestions):

   * Show me the top products. (Should ask for clarification on "top" - by revenue, units sold, etc.)
   * Analyze the sales data. (Should offer suggestions like "show sales by region", "show sales over
     time", etc.)
   * What's interesting in the data? (Should provide a few interesting insights or starting points
     for analysis.)


  More Complex Queries:

   * What is the correlation between units sold and net revenue?
   * Show the seasonality of sales. (This might be vague depending on the data, and could trigger
     suggestions).
   * For each region, what are the top 3 products by net revenue?

  Follow-up Queries (To Test Conversational Context):

   1. First query: Show the total net revenue by region.
   2. Follow-up: Now, show the top 3 products for the region with the highest revenue.

   1. First query: Show me the sales for the "North" region.
   2. Follow-up: Of those, which products are in the "Gadgets" category?
