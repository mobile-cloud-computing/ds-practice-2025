import {Routes, Route, Navigate} from 'react-router-dom';

import './App.css';
import {HomePage} from './layouts/HomePage/HomePage';
import {Footer} from './layouts/NavbarAndFooter/Footer';
import {Navbar} from './layouts/NavbarAndFooter/Navbar';
import {SearchBooksPage} from './layouts/SearchBooksPage/SearchBooksPage';

import ViewSingleBook from "./layouts/ViewSingleBook";
import CheckoutPage from "./CheckoutPage/CheckoutPage";
import CheckoutConfirmation from "./CheckoutPage/CheckoutConfirmation";

export const App = () => {

    return (
        <div className='d-flex flex-column min-vh-100'>
            <Navbar/>
            <div className='flex-grow-1'>
                <Routes>
                    <Route path='/' element={<Navigate replace to='/home'/>}/>
                    <Route path='/home' element={<HomePage/>}/>
                    <Route path='/search' element={<SearchBooksPage/>}/>
                    <Route path='/books/:bookId' element={<ViewSingleBook/>}/>
                    <Route path='/checkout/:bookId' element={<CheckoutPage/>}/>
                    <Route path='/checkout/:bookId/confirmation' element={<CheckoutConfirmation/>}/>

                </Routes>
            </div>
            <Footer/>
        </div>
    );
}
