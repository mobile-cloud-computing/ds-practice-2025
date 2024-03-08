import { Link } from "react-router-dom";
import { Book } from "../../../Api/bookstoreClient";

export const SearchBook: React.FC<{ books: Book }> = (props) => {
    return (
        <div className='card mt-3 shadow-lg p-3 mb-3 bg-body rounded'>
            <div className='row g-0'>
                <div className='col-md-2'>
                    <img src={props.books.image_url || props.books.imageUrl || require('../../../Images/BooksImages/book-luv2code-1000.png')}
                         className='img-fluid rounded-start'
                         alt='Book'
                    />
                </div>
                <div className='col-md-6'>
                    <div className='card-body'>
                        <h5 className='card-title'>{props.books.author}</h5>
                        <h4>{props.books.title}</h4>
                        <p className='card-text'>{props.books.description}</p>
                    </div>
                </div>
                <div className='col-md-4 d-flex justify-content-center align-items-center'>
                    <Link to={`/books/${props.books.id}`} type='button' className='btn btn-outline-success btn-lg'>
                        View Details</Link>
                </div>
            </div>
        </div>
    );
};
