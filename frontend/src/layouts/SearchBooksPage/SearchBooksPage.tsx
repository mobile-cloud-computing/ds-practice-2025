import React, { useCallback, useEffect, useMemo, useState } from 'react';
import debounce from 'lodash.debounce';
import { Pagination } from '../Utils/Pagination';
import { SpinnerLoading } from '../Utils/SpinnerLoading';
import { SearchBook } from './components/SearchBook';
import { Link } from "react-router-dom";
import { AsyncActionType, useGetBooks } from '../../hooks/bookstore.hook';
import { Book } from '../../Api/bookstoreClient';


export const SearchBooksPage = () => {
    const [currentPage, setCurrentPage] = useState(1);
    const [booksPerPage] = useState(5);
    const [totalAmountOfBooks, setTotalAmountOfBooks] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [search, setSearch] = useState('');
    const [searchResults, setSearchResults] = useState<Book[]>([]);

    const { state: bookState } = useGetBooks();

    const currentBooks = useMemo(() => {
        if (searchResults.length > 0) {
            return searchResults.slice((currentPage - 1) * booksPerPage, currentPage * booksPerPage)
        }
        return [];
    }, [searchResults, currentPage, booksPerPage]);


    useEffect(() => {
        console.log({bookState});
        if (bookState.state === AsyncActionType.Success) {
            const loadedBooks = bookState.payload ?? []
            setSearchResults(loadedBooks);
            updatePagination(loadedBooks.length);
        }
    }, [bookState.state, bookState.payload]);

    const handleSearch = useCallback((searchValue: string) => {
        const books = bookState.payload ?? [];
        const filteredResults = books.filter(item =>
            item.title.toLowerCase().includes(searchValue.toLowerCase())
        );
        setSearchResults(filteredResults);
        updatePagination(filteredResults.length);
    }, [bookState.payload]);

    const debouncedSearch = debounce(handleSearch, 300);

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setSearch(value);
        debouncedSearch(value);
    };

    const updatePagination = (totalItems: number) => {
        setTotalAmountOfBooks(totalItems);
        setTotalPages(Math.ceil(totalItems / booksPerPage));
        setCurrentPage(1);
    };

    const paginate = (pageNumber: number) => setCurrentPage(pageNumber);
    const indexOfLastBook = currentPage * booksPerPage;
    const indexOfFirstBook = indexOfLastBook - booksPerPage;


    if (bookState.state === AsyncActionType.Loading) return <SpinnerLoading />;
    if (bookState.state === AsyncActionType.Error) return <div className='container m-5'><p>An error occurred while fetching book data.</p></div>;


    return (
        <div className='container'>
            <div className='row mt-5'>
                <div className='col-6'>
                    <div className='d-flex'>
                        <input
                            className='form-control me-2'
                            type='search'
                            placeholder='Search'
                            aria-labelledby='Search'
                            value={search}
                            onChange={handleSearchChange}
                        />
                    </div>
                </div>
            </div>
            {totalAmountOfBooks > 0 ? (
                <>
                    <div className='mt-3'>
                        <h5>Number of results: ({totalAmountOfBooks})</h5>
                    </div>
                    <p>
                        {indexOfFirstBook + 1} to {indexOfFirstBook + currentBooks.length} of{' '}
                        {totalAmountOfBooks} items:
                    </p>
                    {currentBooks.map((book: Book) => (
                        <SearchBook books={book} key={book.id} />
                    ))}
                </>
            ) : (
                <div className='m-5'>
                    <h3>No book found</h3>
                    <Link to="#" type='button' className='btn-outline-success btn-md px-4 me-md-2 fw-bold text-white'>
                        Bookstore Services Services
                    </Link>
                </div>
            )}
            {totalPages > 1 && <Pagination currentPage={currentPage} totalPages={totalPages} paginate={paginate} />}
        </div>
    );
};
