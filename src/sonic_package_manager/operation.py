#!/usr/bin/env python

from collections import defaultdict

class Operation:
    ''' Package installation operation interface. '''

    def execute(self):
        ''' Execute the operation. If the operation fails, raises a PackageManagerError.
            This method is required to cleanup on failure.

            Args:
                self (Operation): Operation instance.
            Returns:
                None.
        '''

        raise NotImplementedError

    def restore(self):
        ''' Restore the system from operation done in execute().
            This operation restore should not fail normally, but it is required to leave
            the system in a clean state.

            Args:
                self (Operation): Operation instance.
            Returns:
                None.
        '''

        raise NotImplementedError
