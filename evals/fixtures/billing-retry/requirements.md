# Credit delivery

For an authenticated payment provider event with a unique event ID, credit the account exactly once even if the provider retries delivery. The database operations in this example each commit independently. A process crash may occur between any two operations. Provider authentication is handled before this function and is outside this review.
