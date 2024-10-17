# Overview

This repository contains the implementation of **Step 10** from the [Tryton training tutorial](https://github.com/coopengo/tryton-training/wiki). 

Developed as part of the onboarding process for developers at Coopengo, this project focuses on building a library management module within the Tryton framework. 

Through this exercise, I learned how to extend Tryton functionnalities by creating a new module that introduces user management and book borrowing functionality, while reinforcing key concepts such as model extension, wizard creation, and custom search functions.

# Installation

Please go on to the Tryton training [setup page](https://github.com/coopengo/tryton-training/wiki/5.0-setup) or find more information on the [wiki](https://github.com/coopengo/tryton-training/wiki) for instructions on how to setup Tryton and use this module.

# Implemented features

- Manage book **locations** (floors/rooms/shelves).
- View **rooms**, **shelves**, and **book copies** with availability.
- Special locations:
  - **Reserve**: Non-borrowable book copies.
  - **Quarantine**: Returned books stay 7 days before returning to shelves.
- Move book copies between shelves or to the reserve.
- Set shelf destination for bulk purchases, reserve some copies.
- Bonus features:
  - Move books from the reserve for borrowing.
  - Book reservation system.
  - Find copies of the same book across different rooms.
